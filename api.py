# api.py - VERSIÓN CON FRONTEND REACT INTEGRADO
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os

app = Flask(__name__, static_folder='react-build', static_url_path='')   # Deshabilitar static folder por defecto
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
# Configuración DINÁMICA
# =========================
def obtener_base_url():
    """Obtiene la BASE_URL desde datos_hosting - VERSIÓN DINÁMICA"""
    try:
        # 1. PRIMERO: Leer de la tabla datos_hosting de forma DINÁMICA
        try:
            # Configuración mínima para acceder a databaseapp
            config_temp = {
                'host': os.environ.get('MYSQLHOST', 'localhost'),
                'user': os.environ.get('MYSQLUSER', 'root'),
                'password': os.environ.get('MYSQLPASSWORD', ''),
                'database': 'databaseapp',  # ✅ Donde está datos_hosting
                'port': int(os.environ.get('MYSQLPORT', 3306)),
            }
            
            conn_temp = mysql.connector.connect(**config_temp)
            cursor = conn_temp.cursor(dictionary=True)
            cursor.execute("SELECT base_url FROM datos_hosting WHERE activo = 1 LIMIT 1")
            config = cursor.fetchone()
            conn_temp.close()
            
            if config and config['base_url']:
                base_url = config['base_url'].rstrip('/')
                print(f"🌐 URL desde datos_hosting: {base_url}")
                return base_url
            else:
                print("⚠️  No se encontró base_url en datos_hosting")
        except Exception as e:
            print(f"⚠️  No se pudo obtener URL de tabla: {e}")
        
        # 2. SEGUNDO: Usar request actual (dinámico)
        if hasattr(request, 'url_root') and request.url_root:
            base_url = request.url_root.rstrip('/')
            print(f"🌐 URL detectada automáticamente: {base_url}")
            return base_url
        
        # 3. TERCERO: Fallback genérico
        return os.environ.get('BASE_URL', 'http://localhost:5000')
        
    except Exception:
        return "http://localhost:5000"
INICIALIZADO = False

# =========================
# Funciones utilitarias
# =========================
def inicializar_servidor():
    """Inicializa el servidor - VERSIÓN CON REACT"""
    global INICIALIZADO
    
    if INICIALIZADO:
        return
    
    print("🚀 INICIANDO SERVIDOR API - CON FRONTEND REACT")
    print(f"🌐 Host BD: {os.environ.get('MYSQLHOST', 'No configurado')}")
    print(f"👤 Usuario BD: {os.environ.get('MYSQLUSER', 'No configurado')}")
    print(f"🗄️  Base de datos: {os.environ.get('MYSQLDATABASE', 'No configurado')}")
    
    # Verificar frontend React
    frontend_activo = verificar_frontend_react()
    if frontend_activo:
        print("🎯 Frontend React integrado y listo")
    else:
        print("⚠️  Frontend React no encontrado - Solo APIs disponibles")
    
    INICIALIZADO = True

def conectar_base_datos():
    """Conexión SIMPLIFICADA - usa configuración directa de Railway"""
    try:
        print("🔗 Conectando via variables de entorno de Railway...")
        
        config = {
            'host': os.environ.get('MYSQLHOST'),
            'user': os.environ.get('MYSQLUSER'),
            'password': os.environ.get('MYSQLPASSWORD'),
            'database': os.environ.get('MYSQLDATABASE'),
            'port': int(os.environ.get('MYSQLPORT', 3306)),
        }
        
        print(f"🔧 Config: {config['host']}:{config['port']} -> {config['database']}")
        
        conexion = mysql.connector.connect(**config)
        
        if conexion.is_connected():
            print("✅ Conectado via variables entorno")
            return conexion
        else:
            raise Exception("Conexión falló")
            
    except Error as e:
        print(f"❌ Error conectando: {e}")
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
# SERVIR FRONTEND REACT
# =========================
@app.route("/")
def servir_frontend():
    """Servir el frontend React principal"""
    try:
        return send_from_directory(REACT_BUILD_PATH, 'index.html')
    except Exception as e:
        # Si no hay frontend, mostrar info de APIs
        return jsonify({
            "mensaje": "Backend API funcionando - Frontend no configurado",
            "status": "api_activa",
            "endpoints_disponibles": [
                "/api/info-servidor",
                "/api/configuracion", 
                "/api/regiones",
                "/api/usuarios",
                "/api/secciones",
                "/api/subsecciones"
            ],
            "frontend": "no_encontrado"
        })

@app.route("/<path:path>")
def servir_react(path):
    """Servir archivos estáticos del React build"""
    try:
        # Si es un archivo que existe en el build, servirlo
        if os.path.exists(os.path.join(REACT_BUILD_PATH, path)):
            return send_from_directory(REACT_BUILD_PATH, path)
        else:
            # Para React Router - siempre servir index.html
            return send_from_directory(REACT_BUILD_PATH, 'index.html')
    except Exception:
        # Fallback a index.html
        return send_from_directory(REACT_BUILD_PATH, 'index.html')

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

@app.route("/api/debug-conexion")
def debug_conexion():
    """Debug completo de la conexión a BD"""
    try:
        print("🔍 Debug: Intentando conectar a databaseapp...")
        
        # 1. Primero intentar conectar a databaseapp
        config_databaseapp = {
            'host': os.environ.get('MYSQLHOST', 'localhost'),
            'user': os.environ.get('MYSQLUSER', 'root'),
            'password': os.environ.get('MYSQLPASSWORD', ''),
            'database': 'databaseapp',
            'port': int(os.environ.get('MYSQLPORT', 3306)),
        }
        
        conn_temp = mysql.connector.connect(**config_databaseapp)
        cursor = conn_temp.cursor(dictionary=True)
        
        # 2. Leer datos_hosting
        cursor.execute("SELECT * FROM datos_hosting WHERE activo = 1 LIMIT 1")
        hosting_config = cursor.fetchone()
        conn_temp.close()
        
        if not hosting_config:
            return jsonify({"error": "No hay configuración en datos_hosting"}), 500
        
        # 3. Intentar conectar con la configuración de datos_hosting
        config_final = {
            'host': hosting_config['host'],
            'user': hosting_config['usuario'],
            'password': hosting_config['password'],
            'database': hosting_config['base_datos'],
            'port': hosting_config['puerto'],
        }
        
        conn_final = mysql.connector.connect(**config_final)
        conn_final.close()
        
        return jsonify({
            "status": "✅ CONEXIÓN EXITOSA",
            "config_databaseapp": {
                "host": config_databaseapp['host'],
                "database": config_databaseapp['database'],
                "conexion_exitosa": True
            },
            "config_datos_hosting": {
                "host": hosting_config['host'],
                "database": hosting_config['base_datos'],
                "puerto": hosting_config['puerto'],
                "conexion_exitosa": True
            }
        })
        
    except Exception as e:
        return jsonify({
            "error": "❌ CONEXIÓN FALLIDA",
            "detalles": str(e)
        }), 500
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
    # Si es una ruta de API, mostrar error JSON
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
                "/api/subsecciones"
            ]
        }), 404
    else:
        # Para rutas del frontend, servir index.html (React Router)
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