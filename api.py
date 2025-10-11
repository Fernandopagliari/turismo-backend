from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os

app = Flask(__name__, static_folder='react-build', static_url_path='')
CORS(app)

def limpiar_columnas_absolutas(item):
    """Convierte rutas absolutas de Windows en rutas relativas"""
    if not item:
        return item
        
    for key, value in item.items():
        if isinstance(value, str) and 'E:/Sistemas' in value:
            # Extraer solo el nombre del archivo
            if '/' in value:
                nombre_archivo = value.split('/')[-1]
            else:
                nombre_archivo = value.split('\\')[-1]
            item[key] = f"assets/imagenes/{nombre_archivo}"
            print(f"🔄 Limpiando ruta: {value} → {item[key]}")
    
    return item

# =========================
# CONFIGURACIÓN BÁSICA
# =========================
REACT_BUILD_PATH = os.path.join(os.path.dirname(__file__), 'react-build')

def conectar_bd():
    """Conexión simple a la base de datos"""
    try:
        config = {
            'host': os.environ.get('MYSQLHOST'),
            'user': os.environ.get('MYSQLUSER'),
            'password': os.environ.get('MYSQLPASSWORD'),
            'database': os.environ.get('MYSQLDATABASE'),
            'port': int(os.environ.get('MYSQLPORT', 3306)),
        }
        return mysql.connector.connect(**config)
    except Exception as e:
        print(f"❌ Error BD: {e}")
        return None

# =================================================================
# 1. PRIMERO - TODAS LAS RUTAS API (CRÍTICO: DEBEN IR PRIMERO)
# =================================================================

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "message": "Servidor funcionando"})

@app.route("/api/info-servidor")
def info_servidor():
    conn = conectar_bd()
    bd_conectada = conn is not None
    if conn:
        conn.close()
    
    return jsonify({
        "status": "servidor_activo",
        "mensaje": "API funcionando correctamente", 
        "conexion_bd": bd_conectada,
        "frontend_react": os.path.exists(os.path.join(REACT_BUILD_PATH, 'index.html'))
    })

# Funciones originales
def get_configuracion():
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "No hay conexión a BD"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                id_config,
                titulo_app,
                logo_app,
                logo_app_ruta_relativa,
                icono_hamburguesa,
                icono_hamburguesa_ruta_relativa,
                icono_cerrar, 
                icono_cerrar_ruta_relativa,
                hero_titulo,
                hero_imagen,
                hero_imagen_ruta_relativa,
                footer_texto,
                direccion_facebook,
                direccion_instagram,
                direccion_twitter,
                direccion_youtube,
                correo_electronico,
                habilitar
            FROM configuracion_app WHERE habilitar = 1 LIMIT 1
        """)
        config = cursor.fetchone()
        conn.close()
        
        if config:
            print("✅ API Config - Configuración cargada")
        else:
            print("⚠️ API Config - No hay configuración activa")
            
        return jsonify(config if config else {})
    except Exception as e:
        print(f"❌ API Config - Error: {e}")
        return jsonify({"error": str(e)}), 500

def get_usuarios():
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "No hay conexión a BD"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                id_usuario,
                apellido_nombres_usuario,
                dni_usuario,
                domicilio_usuario,
                localidad_usuario,
                provincia_usuario,
                telefono_usuario,
                email_usuario,
                nombre_usuario_acceso,
                foto_usuario,
                rol_usuario,
                activo
            FROM usuarios WHERE activo = 1 ORDER BY apellido_nombres_usuario
        """)
        usuarios = cursor.fetchall()
        conn.close()
        
        print(f"✅ API Usuarios - {len(usuarios)} usuarios activos")
        return jsonify(usuarios)
    except Exception as e:
        print(f"❌ API Usuarios - Error: {e}")
        return jsonify({"error": str(e)}), 500

def get_regiones():
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "No hay conexión a BD"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                id_region_zona,
                nombre_region_zona,
                imagen_region_zona_ruta_relativa,
                habilitar,
                orden
            FROM regiones_zonas WHERE habilitar = 1 ORDER BY orden ASC
        """)
        regiones = cursor.fetchall()
        conn.close()
        
        print(f"✅ API Regiones - {len(regiones)} regiones")
        return jsonify(regiones)
    except Exception as e:
        print(f"❌ API Regiones - Error: {e}")
        return jsonify({"error": str(e)}), 500

def get_secciones():
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500
        
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id_seccion, nombre_seccion,
                   icono_seccion, habilitar, orden
            FROM secciones WHERE habilitar = 1 ORDER BY orden
        """)
        secciones = cursor.fetchall()
        
        print(f"🔍 DEBUG: Encontradas {len(secciones)} secciones")

        for i, seccion in enumerate(secciones):
            print(f"🔍 Procesando sección {seccion['id_seccion']}: {seccion['nombre_seccion']}")
            
            cursor.execute("""
                SELECT id_sub_seccion, id_seccion, id_region_zona, nombre_sub_seccion,
                    domicilio, latitud, longitud, distancia, numero_telefono,
                    imagen_ruta_relativa, icono_ruta_relativa, itinerario_maps,
                    habilitar, fecha_desactivacion, orden, destacado,
                    foto1_ruta_relativa, foto2_ruta_relativa, foto3_ruta_relativa,
                    foto4_ruta_relativa
                FROM sub_secciones WHERE id_seccion = %s AND habilitar = 1 ORDER BY orden
            """, (seccion["id_seccion"],))
            
            subsecciones = cursor.fetchall()
            print(f"   📊 Subsecciones encontradas: {len(subsecciones)}")
            
            seccion["subsecciones"] = subsecciones
            secciones[i] = seccion

        conn.close()
        
        total_subsecciones = sum(len(s.get('subsecciones', [])) for s in secciones)
        print(f"✅ FINAL: {len(secciones)} secciones con {total_subsecciones} subsecciones")
        
        return jsonify(secciones)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

# RUTAS EXACTAS QUE EL FRONTEND NECESITA
@app.route("/api/configuracion")
def api_configuracion():
    """Ruta exacta que el frontend espera"""
    return get_configuracion()

@app.route("/api/regiones")  
def api_regiones():
    """Ruta exacta que el frontend espera"""
    return get_regiones()

@app.route("/api/secciones")
def api_secciones():
    """Ruta exacta que el frontend espera"""
    return get_secciones()

@app.route("/api/usuarios")
def api_usuarios():
    """Ruta exacta que el frontend espera"""
    return get_usuarios()

@app.route("/api/subsecciones")
def api_subsecciones():
    """Ruta para todas las subsecciones"""
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "No hay conexión a BD"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id_sub_seccion, id_seccion, id_region_zona, nombre_sub_seccion,
                domicilio, latitud, longitud, distancia, numero_telefono,
                imagen_ruta_relativa, icono_ruta_relativa, itinerario_maps,
                habilitar, fecha_desactivacion, orden, destacado,
                foto1_ruta_relativa, foto2_ruta_relativa, foto3_ruta_relativa,
                foto4_ruta_relativa
            FROM sub_secciones WHERE habilitar = 1 ORDER BY orden
        """)
        subsecciones = cursor.fetchall()
        conn.close()
        
        print(f"✅ API Subsecciones - {len(subsecciones)} subsecciones")
        return jsonify(subsecciones)
    except Exception as e:
        print(f"❌ API Subsecciones - Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/regiones_zonas")
def api_regiones_zonas():
    """Alias para compatibilidad"""
    return get_regiones()

# =================================================================
# 2. AL FINAL - RUTAS PARA SERVIR EL FRONTEND REACT
# =================================================================

@app.route("/static-assets/<path:filename>")
def servir_assets(filename):
    assets_path = os.path.join(os.path.dirname(__file__), 'assets')
    return send_from_directory(assets_path, filename)

@app.route("/")
def servir_frontend():
    return send_from_directory(REACT_BUILD_PATH, 'index.html')

@app.route("/<path:path>")
def servir_react(path):
    try:
        file_path = os.path.join(REACT_BUILD_PATH, path)
        if os.path.exists(file_path):
            return send_from_directory(REACT_BUILD_PATH, path)
        else:
            return send_from_directory(REACT_BUILD_PATH, 'index.html')
    except:
        return send_from_directory(REACT_BUILD_PATH, 'index.html')

# =========================
# MANEJO DE ERRORES
# =========================
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({
            "error": "Endpoint no encontrado",
            "mensaje": "La ruta API solicitada no existe"
        }), 404
    else:
        return send_from_directory(REACT_BUILD_PATH, 'index.html')

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Error interno del servidor",
        "mensaje": "Ocurrió un error inesperado"
    }), 500

# =========================
# INICIO DE LA APLICACIÓN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)