# api.py - VERSIÓN COMPLETAMENTE DINÁMICA PARA CUALQUIER SERVIDOR - CORREGIDO
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os

app = Flask(__name__)
CORS(app)

# =========================
# Configuración DINÁMICA
# =========================
def obtener_base_url():
    """Obtiene la BASE_URL dinámicamente del entorno"""
    try:
        # 1. Primero intenta desde variables de entorno
        base_url = os.environ.get('BASE_URL')
        
        # 2. Si no existe y estamos en un contexto de request, la genera desde la request
        if not base_url and hasattr(request, 'url_root'):
            base_url = request.url_root.rstrip('/')
        
        # 3. Si todavía no hay base_url, usa una por defecto basada en el entorno
        if not base_url:
            # Para Railway
            railway_url = os.environ.get('RAILWAY_STATIC_URL')
            if railway_url:
                base_url = railway_url
            else:
                # Para otros entornos
                base_url = "https://turismo-regional.up.railway.app"
        
        # 4. Asegurar HTTPS en producción
        if base_url.startswith('http://') and ('railway' in base_url or 'heroku' in base_url):
            base_url = base_url.replace('http://', 'https://')
        
        return base_url
    except Exception:
        # Fallback seguro
        return "https://turismo-regional.up.railway.app"

INICIALIZADO = False

# =========================
# Funciones utilitarias
# =========================
def inicializar_servidor():
    """Inicializa el servidor - VERSIÓN DINÁMICA"""
    global INICIALIZADO
    
    if INICIALIZADO:
        return
    
    print("🚀 INICIANDO SERVIDOR API - VERSIÓN UNIVERSAL")
    print(f"🌐 Host BD: {os.environ.get('MYSQLHOST', 'No configurado')}")
    print(f"👤 Usuario BD: {os.environ.get('MYSQLUSER', 'No configurado')}")
    print(f"🗄️  Base de datos: {os.environ.get('MYSQLDATABASE', 'No configurado')}")
    INICIALIZADO = True

def conectar_base_datos():
    """Conecta a la base de datos de forma DINÁMICA"""
    try:
        # Obtener configuración desde variables de entorno
        config = {
            'host': os.environ.get('MYSQLHOST'),
            'user': os.environ.get('MYSQLUSER'),
            'password': os.environ.get('MYSQLPASSWORD'),
            'database': os.environ.get('MYSQLDATABASE'),
            'port': int(os.environ.get('MYSQLPORT', 3306)),
            'connect_timeout': 10
        }
        
        # Verificar que tenemos configuración mínima
        if not config['host'] or not config['user']:
            raise Exception("Configuración de BD incompleta en variables de entorno")
        
        print(f"🔗 Conectando a: {config['host']}:{config['port']} -> {config['database']}")
        conexion = mysql.connector.connect(**config)
        
        if conexion.is_connected():
            print(f"✅ Conectado a BD: {config['host']} -> {config['database']}")
            return conexion
        else:
            raise Exception("No se pudo establecer conexión")
            
    except Error as e:
        print(f"❌ Error conectando a BD: {e}")
        raise Exception(f"Error de conexión con BD: {str(e)}")

def verificar_conexion_remota():
    """Verifica conexión a la base de datos"""
    try:
        conn = conectar_base_datos()
        cursor = conn.cursor(dictionary=True)
        
        tablas_verificar = [
            "configuracion_app",
            "regiones_zonas", 
            "secciones",
            "sub_secciones",
            "usuarios"
        ]
        
        resultados = {}
        for tabla in tablas_verificar:
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {tabla}")
                resultado = cursor.fetchone()
                count = resultado['count'] if resultado else 0
                resultados[tabla] = count
                print(f"📊 {tabla}: {count} registros")
            except Exception as e:
                print(f"⚠️  Tabla {tabla} no disponible: {e}")
                resultados[tabla] = -1
        
        conn.close()
        return resultados
        
    except Exception as e:
        print(f"❌ No se pudo verificar conexión: {e}")
        return None

def url_completa(ruta_relativa: str) -> str:
    """Convierte rutas relativas en URL completas de forma DINÁMICA"""
    if not ruta_relativa:
        return None
    
    base_url = obtener_base_url()
    ruta_limpia = ruta_relativa.replace("\\", "/").lstrip("/")
    
    # Si la ruta no empieza con assets/, agregarlo
    if not ruta_limpia.startswith("assets/"):
        ruta_limpia = f"assets/{ruta_limpia}"
    
    return f"{base_url}/{ruta_limpia}"

def limpiar_columnas_absolutas(row: dict) -> dict:
    """Convierte columnas con 'ruta' en URL completa"""
    if not row:
        return {}
        
    limpio = {}
    for key, value in row.items():
        if value and any(patron in key.lower() for patron in ['ruta', 'imagen', 'icono', 'foto', 'logo']):
            limpio[key] = url_completa(value)
        else:
            limpio[key] = value
    return limpio

# =========================
# Middleware
# =========================
@app.before_request
def antes_de_peticion():
    if not INICIALIZADO:
        inicializar_servidor()

# =========================
# Endpoints PRINCIPALES
# =========================
@app.route("/", methods=["GET"])
def health_check():
    """Endpoint principal de verificación"""
    base_url = obtener_base_url()
    return jsonify({
        "status": "ok",
        "mensaje": "Servidor API funcionando correctamente",
        "base_url": base_url,
        "entorno": "producción",
        "servidor": "universal",
        "endpoints_disponibles": [
            "/api/info-servidor",
            "/api/configuracion", 
            "/api/regiones",
            "/api/usuarios",
            "/api/secciones",
            "/api/subsecciones"
        ]
    })

@app.route("/api/info-servidor", methods=["GET"])
def get_info_servidor():
    """Información completa del servidor"""
    try:
        base_url = obtener_base_url()
        estado_conexion = verificar_conexion_remota()
        
        return jsonify({
            "base_url": base_url,
            "status": "servidor_activo",
            "mensaje": "API funcionando correctamente",
            "entorno": "producción",
            "conexion_bd": bool(estado_conexion),
            "detalles_tablas": estado_conexion,
            "configuracion_bd": {
                "host": os.environ.get('MYSQLHOST', 'No configurado'),
                "database": os.environ.get('MYSQLDATABASE', 'No configurado'),
                "usuario": os.environ.get('MYSQLUSER', 'No configurado')
            }
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "servidor_con_error"
        }), 500

# =========================
# Endpoints de DATOS
# =========================
@app.route("/api/configuracion", methods=["GET"])
def get_configuracion():
    """Obtener configuración de la aplicación"""
    try:
        conn = conectar_base_datos()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM configuracion_app LIMIT 1")
        config = cursor.fetchone()
        conn.close()

        if config:
            config = limpiar_columnas_absolutas(config)

        return jsonify(config if config else {})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/regiones", methods=["GET"])
@app.route("/api/regiones_zonas", methods=["GET"])
def get_regiones_zonas():
    """Obtener regiones y zonas (endpoint dual)"""
    try:
        conn = conectar_base_datos()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM regiones_zonas WHERE habilitar = 1 ORDER BY orden ASC")
        regiones = cursor.fetchall()
        conn.close()
        
        regiones = [limpiar_columnas_absolutas(region) for region in regiones]
        return jsonify(regiones)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/usuarios", methods=["GET"])
def get_usuarios():
    """Obtener usuarios"""
    try:
        conn = conectar_base_datos()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE activo = 1")
        usuarios = cursor.fetchall()
        conn.close()
        
        usuarios = [limpiar_columnas_absolutas(usuario) for usuario in usuarios]
        return jsonify(usuarios)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/secciones", methods=["GET"])
def get_secciones():
    """Obtener secciones con sus subsecciones"""
    try:
        conn = conectar_base_datos()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM secciones WHERE habilitar = 1 ORDER BY orden")
        secciones = cursor.fetchall()

        for i, seccion in enumerate(secciones):
            seccion = limpiar_columnas_absolutas(seccion)

            cursor.execute("""
                SELECT ss.*, rz.nombre_region_zona 
                FROM sub_secciones ss
                LEFT JOIN regiones_zonas rz ON ss.id_region_zona = rz.id_region_zona
                WHERE ss.id_seccion = %s AND ss.habilitar = 1 
                ORDER BY ss.orden
            """, (seccion["id_seccion"],))
            
            subsecciones = cursor.fetchall()
            subsecciones = [limpiar_columnas_absolutas(sub) for sub in subsecciones]
            seccion["subsecciones"] = subsecciones
            secciones[i] = seccion

        conn.close()
        return jsonify(secciones)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/subsecciones", methods=["GET"])
def get_subsecciones():
    """Obtener todas las subsecciones"""
    try:
        conn = conectar_base_datos()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ss.*, s.nombre_seccion, rz.nombre_region_zona 
            FROM sub_secciones ss
            LEFT JOIN secciones s ON ss.id_seccion = s.id_seccion
            LEFT JOIN regiones_zonas rz ON ss.id_region_zona = rz.id_region_zona
            WHERE ss.habilitar = 1 
            ORDER BY ss.orden
        """)
        subsecciones = cursor.fetchall()
        conn.close()
        
        subsecciones = [limpiar_columnas_absolutas(sub) for sub in subsecciones]
        return jsonify(subsecciones)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# Endpoints de ARCHIVOS ESTÁTICOS
# =========================
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Servir archivos estáticos"""
    try:
        return send_from_directory('assets', filename)
    except Exception as e:
        return jsonify({"error": f"Archivo no encontrado: {filename}"}), 404

# =========================
# Manejo de errores
# =========================
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint no encontrado",
        "mensaje": "La ruta solicitada no existe",
        "endpoints_disponibles": [
            "/",
            "/api/info-servidor",
            "/api/configuracion", 
            "/api/regiones",
            "/api/usuarios",
            "/api/secciones",
            "/api/subsecciones"
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Error interno del servidor",
        "mensaje": "Ocurrió un error inesperado"
    }), 500

# =========================
# Main
# =========================
if __name__ == "__main__":
    # Este bloque solo se ejecuta en desarrollo local
    inicializar_servidor()
    print("🔍 Verificando conexión...")
    estado = verificar_conexion_remota()
    if estado:
        print("✅ Conexión verificada")
    else:
        print("⚠️  Problemas con conexión")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)