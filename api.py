# api.py - VERSIÓN CON FRONTEND REACT INTEGRADO
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os

app = Flask(__name__, static_folder='react-build', static_url_path='')
CORS(app)

# =========================
# Configuración FRONTEND REACT
# =========================
REACT_BUILD_PATH = os.path.join(os.path.dirname(__file__), 'react-build')

def verificar_frontend_react():
    """Verificar si el frontend React está disponible"""
    index_path = os.path.join(REACT_BUILD_PATH, 'index.html')
    existe = os.path.exists(index_path)
    print(f"🔍 Frontend React: {'✅ DISPONIBLE' if existe else '❌ NO ENCONTRADO'}")
    return existe

# =========================
# Configuración UNIVERSAL
# =========================
def obtener_configuracion_hosting():
    """Obtiene configuración desde la tabla datos_hosting - VERSIÓN UNIVERSAL"""
    try:
        # 1. PRIMERO: Variables de entorno MÍNIMAS para conectar a databaseapp
        config_temp = {
            'host': os.environ.get('MYSQLHOST', 'localhost'),
            'user': os.environ.get('MYSQLUSER', 'root'),
            'password': os.environ.get('MYSQLPASSWORD', ''),
            'database': 'databaseapp',  # BD donde está datos_hosting
            'port': int(os.environ.get('MYSQLPORT', 3306)),
            'connect_timeout': 10
        }
        
        print(f"🔗 Conectando a databaseapp: {config_temp['host']} -> {config_temp['database']}")
        
        conn = mysql.connector.connect(**config_temp)
        cursor = conn.cursor(dictionary=True)
        
        # 2. Leer configuración activa de datos_hosting
        cursor.execute("SELECT * FROM datos_hosting WHERE activo = 1 ORDER BY id LIMIT 1")
        hosting_config = cursor.fetchone()
        conn.close()
        
        if not hosting_config:
            raise Exception("No hay configuración activa en datos_hosting")
        
        print(f"✅ Configuración encontrada: {hosting_config['host']} -> {hosting_config['base_datos']}")
        return hosting_config
        
    except Exception as e:
        print(f"❌ Error leyendo datos_hosting: {e}")
        raise Exception(f"No se pudo obtener configuración: {str(e)}")

def obtener_base_url():
    """Obtiene BASE_URL desde datos_hosting o request"""
    try:
        # 1. Intentar desde datos_hosting
        try:
            hosting_config = obtener_configuracion_hosting()
            if hosting_config and hosting_config.get('base_url'):
                base_url = hosting_config['base_url'].rstrip('/')
                print(f"🌐 URL desde datos_hosting: {base_url}")
                return base_url
        except Exception as e:
            print(f"⚠️  No se pudo obtener URL de tabla: {e}")
        
        # 2. Usar request actual
        if hasattr(request, 'url_root') and request.url_root:
            base_url = request.url_root.rstrip('/')
            print(f"🌐 URL detectada automáticamente: {base_url}")
            return base_url
        
        # 3. Fallback genérico
        return os.environ.get('BASE_URL', 'http://localhost:5000')
        
    except Exception:
        return "http://localhost:5000"

INICIALIZADO = False

# =========================
# Funciones utilitarias - UNIVERSALES
# =========================
def inicializar_servidor():
    """Inicializa el servidor"""
    global INICIALIZADO
    
    if INICIALIZADO:
        return
    
    print("🚀 INICIANDO SERVIDOR API - CONFIGURACIÓN UNIVERSAL")
    print("🎯 Usando tabla datos_hosting para configuración")
    
    # Verificar frontend React
    frontend_activo = verificar_frontend_react()
    if frontend_activo:
        print("✅ Frontend React integrado y listo")
    else:
        print("⚠️  Frontend React no encontrado")
    
    INICIALIZADO = True

def conectar_base_datos():
    """Conecta a la base de datos usando datos_hosting - VERSIÓN UNIVERSAL"""
    try:
        print("🔗 Conectando via datos_hosting...")
        
        # 1. Obtener configuración desde datos_hosting
        hosting_config = obtener_configuracion_hosting()
        
        # 2. Conectar usando la configuración de la tabla
        config = {
            'host': hosting_config['host'],
            'user': hosting_config['usuario'],
            'password': hosting_config['password'],
            'database': hosting_config['base_datos'],
            'port': hosting_config['puerto'],
            'connect_timeout': 10
        }
        
        print(f"🔧 Conectando a: {config['host']}:{config['port']} -> {config['database']}")
        
        conexion = mysql.connector.connect(**config)
        
        if conexion.is_connected():
            print("✅ Conexión exitosa via datos_hosting")
            return conexion
        else:
            raise Exception("No se pudo establecer conexión")
            
    except Error as e:
        print(f"❌ Error conectando via datos_hosting: {e}")
        
        # FALLBACK: Intentar con variables de entorno directas
        try:
            print("🔄 Intentando conexión directa...")
            config_fallback = {
                'host': os.environ.get('MYSQLHOST'),
                'user': os.environ.get('MYSQLUSER'),
                'password': os.environ.get('MYSQLPASSWORD'),
                'database': os.environ.get('MYSQLDATABASE'),
                'port': int(os.environ.get('MYSQLPORT', 3306)),
            }
            
            if all([config_fallback['host'], config_fallback['user'], config_fallback['database']]):
                conexion = mysql.connector.connect(**config_fallback)
                if conexion.is_connected():
                    print("✅ Conexión exitosa via fallback")
                    return conexion
        except Error as fallback_error:
            print(f"❌ Fallback también falló: {fallback_error}")
        
        raise Exception(f"Error de conexión BD: {str(e)}")

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
    """Convierte rutas relativas en URL completas"""
    if not ruta_relativa:
        return None
    
    base_url = obtener_base_url()
    ruta_limpia = ruta_relativa.replace("\\", "/").lstrip("/")
    return f"{base_url}/assets/{ruta_limpia}"

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
# SERVIR FRONTEND REACT
# =========================
@app.route("/")
def servir_frontend():
    """Servir el frontend React principal"""
    try:
        return send_from_directory(REACT_BUILD_PATH, 'index.html')
    except Exception as e:
        return jsonify({
            "mensaje": "Backend API funcionando - Frontend no disponible",
            "error": str(e)
        }), 500

@app.route("/<path:path>")
def servir_react(path):
    """Servir archivos estáticos del React build"""
    try:
        file_path = os.path.join(REACT_BUILD_PATH, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(REACT_BUILD_PATH, path)
        else:
            return send_from_directory(REACT_BUILD_PATH, 'index.html')
    except Exception:
        return send_from_directory(REACT_BUILD_PATH, 'index.html')

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Servir archivos estáticos desde react-build/assets/"""
    try:
        assets_path = os.path.join(REACT_BUILD_PATH, 'assets')
        return send_from_directory(assets_path, filename)
    except Exception as e:
        print(f"❌ Error sirviendo asset {filename}: {e}")
        return jsonify({"error": f"Archivo no encontrado: {filename}"}), 404

# =========================
# Endpoints de DEBUG - UNIVERSALES
# =========================
@app.route("/api/debug-conexion")
def debug_conexion():
    """Debug de conexión usando datos_hosting"""
    try:
        print("🔍 Debug: Verificando configuración datos_hosting...")
        
        # 1. Obtener configuración
        hosting_config = obtener_configuracion_hosting()
        
        # 2. Intentar conexión
        config = {
            'host': hosting_config['host'],
            'user': hosting_config['usuario'],
            'password': hosting_config['password'],
            'database': hosting_config['base_datos'],
            'port': hosting_config['puerto'],
        }
        
        print(f"🔧 Config desde datos_hosting: {config}")
        
        conn = mysql.connector.connect(**config)
        
        if conn.is_connected():
            # Verificar tablas
            cursor = conn.cursor(dictionary=True)
            tablas = ['regiones_zonas', 'secciones', 'usuarios', 'configuracion_app']
            resultados = {}
            
            for tabla in tablas:
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {tabla}")
                    count = cursor.fetchone()['count']
                    resultados[tabla] = f"✅ {count} registros"
                except Exception as e:
                    resultados[tabla] = f"❌ Error: {str(e)}"
            
            conn.close()
            
            return jsonify({
                "status": "✅ CONEXIÓN EXITOSA via datos_hosting",
                "config_usada": config,
                "tablas": resultados,
                "base_url_desde_tabla": hosting_config.get('base_url')
            })
        else:
            return jsonify({"error": "Conexión falló"}), 500
            
    except Exception as e:
        return jsonify({
            "error": "❌ CONEXIÓN FALLIDA",
            "detalles": str(e)
        }), 500

@app.route("/api/verificar-tablas")
def verificar_tablas():
    """Verificar tablas"""
    return debug_conexion()

# =========================
# Endpoints PRINCIPALES
# =========================
@app.route("/api/info-servidor", methods=["GET"])
def get_info_servidor():
    """Información completa del servidor"""
    try:
        base_url = obtener_base_url()
        estado_conexion = verificar_conexion_remota()
        frontend_activo = verificar_frontend_react()
        
        return jsonify({
            "base_url": base_url,
            "status": "servidor_activo",
            "mensaje": "API funcionando correctamente",
            "entorno": "producción",
            "conexion_bd": bool(estado_conexion),
            "frontend_react": frontend_activo,
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
# Endpoints de DATOS (se mantienen igual)
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
# ✅ RUTA ESPECÍFICA PARA SERVIR ARCHIVOS ESTÁTICOS
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Servir archivos estáticos desde react-build/assets/"""
    try:
        return send_from_directory(os.path.join(app.static_folder, 'assets'), filename)
    except Exception as e:
        print(f"❌ Error sirviendo asset {filename}: {e}")
        return jsonify({"error": f"Archivo no encontrado: {filename}"}), 404
# =========================
# Manejo de errores 
# =========================
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({
            "error": "Endpoint no encontrado",
            "mensaje": "La ruta API solicitada no existe",
            "endpoints_disponibles": [
                "/api/info-servidor",
                "/api/configuracion", 
                "/api/regiones",
                "/api/usuarios",
                "/api/secciones",
                "/api/subsecciones",
                "/api/debug-conexion",
                "/api/verificar-tablas"
            ]
        }), 404
    else:
        try:
            return send_from_directory(REACT_BUILD_PATH, 'index.html')
        except:
            return jsonify({"error": "Frontend no disponible"}), 404

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
    inicializar_servidor()
    print("🔍 Verificando conexión...")
    estado = verificar_conexion_remota()
    if estado:
        print("✅ Conexión verificada via datos_hosting")
    else:
        print("⚠️  Problemas con conexión")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)