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

@app.route("/api/regiones")
@app.route("/api/regiones_zonas")
def get_regiones():
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "No hay conexión a BD"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM regiones_zonas WHERE habilitar = 1 ORDER BY orden ASC")
        regiones = cursor.fetchall()
        conn.close()
        return jsonify(regiones)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/secciones")
def get_secciones():
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "No hay conexión a BD"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM secciones WHERE habilitar = 1 ORDER BY orden")
        secciones = cursor.fetchall()
        conn.close()
        return jsonify(secciones)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/configuracion")
def get_configuracion():
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "No hay conexión a BD"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM configuracion_app LIMIT 1")
        config = cursor.fetchone()
        conn.close()
        return jsonify(config if config else {})
    except Exception as e:
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