# api.py - VERSIÓN COMPLETA Y CORREGIDA
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os

app = Flask(__name__, static_folder='react-build', static_url_path='')
CORS(app)

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

# =========================
# RUTAS PARA FRONTEND REACT
# =========================
@app.route("/")
def servir_frontend():
    return send_from_directory(REACT_BUILD_PATH, 'index.html')

@app.route("/assets/<path:filename>")
def servir_assets(filename):
    return send_from_directory(os.path.join(REACT_BUILD_PATH, 'assets'), filename)

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
# APIs PRINCIPALES
# =========================
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

@app.route("/api/configuracion")
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

@app.route("/api/usuarios")
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

@app.route("/api/regiones")
@app.route("/api/regiones_zonas")
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

@app.route("/api/secciones")
def get_secciones():
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "No hay conexión a BD"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                id_seccion,
                nombre_seccion,
                icono_seccion,
                orden,
                habilitar
            FROM secciones WHERE habilitar = 1 ORDER BY orden
        """)
        secciones = cursor.fetchall()
        conn.close()
        
        print(f"✅ API Secciones - {len(secciones)} secciones")
        return jsonify(secciones)
    except Exception as e:
        print(f"❌ API Secciones - Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/sub-secciones")
def get_sub_secciones():
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "No hay conexión a BD"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                id_sub_seccion,
                id_seccion,
                nombre_sub_seccion, 
                icono_sub_seccion,
                orden,
                habilitar
            FROM sub_secciones WHERE habilitar = 1 ORDER BY orden
        """)
        sub_secciones = cursor.fetchall()
        conn.close()
        
        print(f"✅ API Sub-Secciones - {len(sub_secciones)} sub-secciones")
        return jsonify(sub_secciones)
    except Exception as e:
        print(f"❌ API Sub-Secciones - Error: {e}")
        return jsonify({"error": str(e)}), 500

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