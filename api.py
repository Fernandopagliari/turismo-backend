# api.py
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from database import conectar_base_datos
import os

app = Flask(__name__)
CORS(app)

# =========================
# Configuración de directorio de assets - MODIFICADO
# =========================
def get_base_dir():
    """Determina el directorio base según el entorno"""
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        # En Railway - sube un nivel desde backend/ a turismo-app/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.dirname(current_dir)  # Sube a turismo-app/
    else:
        # En local - tu ruta actual
        return r"E:\Sistemas de app para androide\turismo-app"

BASE_DIR = get_base_dir()
ASSETS_DIR = os.path.join(BASE_DIR, "public", "assets")

print("[DEBUG] Entorno:", "PRODUCCIÓN" if os.environ.get('RAILWAY_ENVIRONMENT') else "LOCAL")
print("[DEBUG] Base del proyecto:", BASE_DIR)
print("[DEBUG] Assets directory:", ASSETS_DIR)


# =========================
# Funciones utilitarias - MODIFICADA url_completa
# =========================
def url_completa(ruta_relativa: str) -> str:
    """Convierte rutas relativas de assets en URL completa"""
    if not ruta_relativa:
        return None
    
    # Determinar la URL base según el entorno
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        # En producción - usa tu dominio de Railway
        base_url = os.environ.get('RAILWAY_STATIC_URL', 'https://tu-app.railway.app')
    else:
        # En local
        base_url = 'http://localhost:5000'
    
    ruta_limpia = ruta_relativa.replace("\\", "/").lstrip("/")
    if not ruta_limpia.startswith("assets/"):
        ruta_limpia = f"assets/{ruta_limpia}"
    
    return f"{base_url}/{ruta_limpia}"


def obtener_rutas_directorio(directorio: str) -> list:
    """Recorre todas las subcarpetas de un directorio y devuelve las rutas relativas"""
    rutas = []
    if not os.path.exists(directorio):
        print(f"[WARNING] Directorio no existe: {directorio}")
        return rutas
    for root, dirs, files in os.walk(directorio):
        for file in files:
            if file.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                ruta_relativa = os.path.relpath(os.path.join(root, file), ASSETS_DIR)
                rutas.append(f"assets/{ruta_relativa.replace(os.sep, '/')}")
    return rutas


def limpiar_columnas_absolutas(row: dict) -> dict:
    """
    Convierte automáticamente cualquier columna que contenga 'ruta' en URL completa.
    Así se ven todas las imágenes de subsecciones y secciones sin problemas.
    """
    limpio = {}
    for key, value in row.items():
        if value and "ruta" in key.lower():  # detecta cualquier columna con 'ruta'
            limpio[key] = url_completa(value)
        else:
            limpio[key] = value
    return limpio

# =========================
# ENDPOINTS (MANTENER IGUAL - NO CAMBIAN)
# =========================
@app.route("/configuracion", methods=["GET"])
def get_configuracion():
    conn = conectar_base_datos()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id_config, titulo_app, logo_app_ruta_relativa,
               icono_hamburguesa_ruta_relativa, icono_cerrar_ruta_relativa,
               hero_titulo, hero_imagen_ruta_relativa, footer_texto,
               direccion_facebook, direccion_instagram, direccion_twitter,
               direccion_youtube, correo_electronico, habilitar
        FROM configuracion_app LIMIT 1
    """)
    config = cursor.fetchone()
    conn.close()

    if config:
        config = limpiar_columnas_absolutas(config)

    return jsonify([config] if config else [])

@app.route("/api/regiones_zonas", methods=["GET"])
def get_regiones_zonas():
    conn = conectar_base_datos()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id_region_zona, nombre_region_zona, 
               imagen_region_zona_ruta_relativa, habilitar, orden
        FROM regiones_zonas
        ORDER BY orden ASC, nombre_region_zona ASC
    """)
    regiones = cursor.fetchall()
    conn.close()
    return jsonify(regiones)

@app.route("/api/secciones", methods=["GET"])
def get_secciones():
    conn = conectar_base_datos()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id_seccion, nombre_seccion,
               icono_seccion, habilitar, orden
        FROM secciones
    """)
    secciones = cursor.fetchall()

    for i, seccion in enumerate(secciones):
        seccion = limpiar_columnas_absolutas(seccion)

        cursor.execute("""
            SELECT id_sub_seccion, id_seccion, id_region_zona, nombre_sub_seccion,
                domicilio, latitud, longitud, distancia, numero_telefono,
                imagen_ruta_relativa, icono_ruta_relativa, itinerario_maps,
                habilitar, fecha_desactivacion, orden, destacado,
                foto1_ruta_relativa, foto2_ruta_relativa, foto3_ruta_relativa,
                foto4_ruta_relativa
            FROM sub_secciones WHERE id_seccion = %s
        """, (seccion["id_seccion"],))
        subsecciones = cursor.fetchall()
        subsecciones = [limpiar_columnas_absolutas(sub) for sub in subsecciones]

        seccion["subsecciones"] = subsecciones
        secciones[i] = seccion

    conn.close()
    return jsonify(secciones)

@app.route("/api/imagenes", methods=["GET"])
def api_imagenes():
    rutas = obtener_rutas_directorio(os.path.join(ASSETS_DIR, "imagenes"))
    return jsonify(rutas)

@app.route("/assets/<path:filename>")
def serve_assets(filename):
    safe_path = os.path.normpath(os.path.join(ASSETS_DIR, filename))
    print("[DEBUG] Buscando archivo en:", safe_path)
    
    # Verificar que el path esté dentro del directorio permitido
    if not safe_path.startswith(ASSETS_DIR):
        return jsonify({"error": "Path no permitido"}), 403
        
    if os.path.isfile(safe_path):
        dir_path = os.path.dirname(safe_path)
        file_name = os.path.basename(safe_path)
        return send_from_directory(dir_path, file_name)
    else:
        return jsonify({"error": "Archivo no encontrado"}), 404

# =========================
# Health check para Railway - NUEVO
# =========================
@app.route("/")
def health_check():
    return jsonify({
        "status": "OK", 
        "message": "API funcionando correctamente",
        "environment": "production" if os.environ.get('RAILWAY_ENVIRONMENT') else "development"
    })

# =========================
# Main - MODIFICADO
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = not bool(os.environ.get('RAILWAY_ENVIRONMENT'))
    app.run(host="0.0.0.0", port=port, debug=debug)