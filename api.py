# -*- coding: utf-8 -*-
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import os
from datetime import datetime

# =========================================================
# 🔧 BASE DIR (CAMBIO CLAVE)
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================================================
# FLASK APP
# =========================================================
# 👉 static = backend assets
# 👉 dist   = frontend (Vite / React)
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, 'static'),
    static_url_path='/static'
)
CORS(app)

# =========================================================
# 🔥 SERVIR IMÁGENES DEL SISTEMA
# =========================================================
@app.route('/static/assets/<path:filename>')
def serve_static_assets(filename):
    """
    Sirve imágenes desde:
    turismo-backend/static/assets/...
    Compatible local + Render
    """
    base_dir = os.path.join(app.root_path, 'static', 'assets')
    return send_from_directory(base_dir, filename)

# =========================================================
# CONFIGURACIÓN BD LOCAL / HOSTING
# =========================================================

def detectar_entorno():
    if os.environ.get('MYSQLHOST') or os.environ.get('RAILWAY_ENVIRONMENT'):
        return 'hosting'
    return 'local'

def conectar_a_bd_local():
    try:
        return mysql.connector.connect(
            host=os.environ.get('LOCAL_DB_HOST', 'localhost'),
            user=os.environ.get('LOCAL_DB_USER', 'root'),
            password=os.environ.get('LOCAL_DB_PASSWORD', ''),
            database=os.environ.get('LOCAL_DB_NAME', 'databaseapp'),
            port=int(os.environ.get('LOCAL_DB_PORT', 3306))
        )
    except Exception as e:
        print(f"❌ Error BD local: {e}")
        return None

def conectar_a_bd_remota():
    try:
        return mysql.connector.connect(
            host=os.environ.get('MYSQLHOST'),
            user=os.environ.get('MYSQLUSER'),
            password=os.environ.get('MYSQLPASSWORD'),
            database=os.environ.get('MYSQLDATABASE'),
            port=int(os.environ.get('MYSQLPORT', 3306))
        )
    except Exception as e:
        print(f"❌ Error BD remota: {e}")
        return None

def obtener_config_desde_tabla(tabla):
    try:
        conn = conectar_a_bd_remota() if detectar_entorno() == 'hosting' else conectar_a_bd_local()
        if not conn:
            raise Exception("Sin conexión a BD")

        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"""
            SELECT host, usuario, password, base_datos, puerto, base_url
            FROM {tabla}
            WHERE activo = 1
            ORDER BY fecha_creacion DESC
            LIMIT 1
        """)
        config = cursor.fetchone()
        conn.close()

        if not config:
            raise Exception("No hay config activa")

        return {
            'host': config['host'],
            'user': config['usuario'],
            'password': config['password'],
            'database': config['base_datos'],
            'port': config['puerto'],
            'base_url': config.get('base_url', '')
        }
    except Exception as e:
        print(f"❌ Error config {tabla}: {e}")
        raise

def conectar_bd():
    try:
        cfg = obtener_config_desde_tabla('datos_hosting')
        return mysql.connector.connect(
            host=cfg['host'],
            user=cfg['user'],
            password=cfg['password'],
            database=cfg['database'],
            port=cfg['port']
        )
    except:
        return conectar_a_bd_remota() if detectar_entorno() == 'hosting' else conectar_a_bd_local()

# =========================================================
# FRONTEND (DIST)
# =========================================================

@app.route('/')
def serve_frontend():
    return send_from_directory(os.path.join(BASE_DIR, 'dist'), 'index.html')

@app.route('/<path:path>')
def serve_dist_files(path):
    return send_from_directory(os.path.join(BASE_DIR, 'dist'), path)

# =========================================================
# API ENDPOINTS
# =========================================================

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "entorno": detectar_entorno()})

@app.route('/api/configuracion')
def obtener_configuracion():
    conn = conectar_bd()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            titulo_app,
            logo_app_ruta_relativa,
            hero_imagen_ruta_relativa,
            footer_texto
        FROM configuracion_app
        WHERE habilitar = 1
        LIMIT 1
    """)
    data = cursor.fetchone() or {}
    conn.close()
    return jsonify(data)

@app.route('/api/secciones')
def obtener_secciones():
    conn = conectar_bd()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id_seccion, nombre_seccion, icono_seccion
        FROM secciones
        WHERE habilitar = 1
        ORDER BY orden
    """)
    secciones = cursor.fetchall()

    for sec in secciones:
        cursor.execute("""
            SELECT *
            FROM sub_secciones
            WHERE id_seccion = %s AND habilitar = 1
            ORDER BY orden
        """, (sec['id_seccion'],))
        sec['subsecciones'] = cursor.fetchall()

    conn.close()
    return jsonify(secciones)

@app.route('/api/regiones')
def obtener_regiones():
    conn = conectar_bd()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT *
        FROM regiones_zonas
        WHERE habilitar = 1
        ORDER BY orden
    """)
    data = cursor.fetchall()
    conn.close()
    return jsonify(data)

# =========================================================
# DEBUG (NO TOCAR)
# =========================================================

@app.route('/api/debug-static')
def debug_static():
    base = os.path.join(BASE_DIR, 'static', 'assets', 'imagenes')
    return jsonify({
        "path": base,
        "exists": os.path.exists(base),
        "folders": os.listdir(base) if os.path.exists(base) else []
    })

# =========================================================
# MAIN
# =========================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 Backend Turismo iniciado")
    print("📁 Sirviendo imágenes desde /static/assets/")
    app.run(
        host='0.0.0.0',
        port=port,
        debug=(detectar_entorno() == 'local')
    )
