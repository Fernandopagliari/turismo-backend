# api.py - BACKEND FLASK + FRONTEND REACT (VITE) INTEGRADO
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os

# =========================
# CONFIGURACIÓN BASE
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_PATH = os.path.join(BASE_DIR, "dist")
ASSETS_PATH = os.path.join(BASE_DIR, "assets")

app = Flask(
    __name__,
    static_folder=DIST_PATH,
    static_url_path=""
)

CORS(app)

INICIALIZADO = False

# =========================
# FRONTEND REACT
# =========================
def verificar_frontend_react():
    index_path = os.path.join(DIST_PATH, "index.html")
    existe = os.path.exists(index_path)
    print(f"🔍 Frontend React: {'✅ DISPONIBLE' if existe else '❌ NO ENCONTRADO'}")
    return existe

# =========================
# BASE URL DINÁMICA
# =========================
def obtener_base_url():
    try:
        base_url = os.environ.get("BASE_URL")

        if not base_url and hasattr(request, "url_root"):
            base_url = request.url_root.rstrip("/")

        if not base_url:
            base_url = "https://turismo-regional.up.railway.app"

        if base_url.startswith("http://") and "railway" in base_url:
            base_url = base_url.replace("http://", "https://")

        return base_url
    except:
        return "https://turismo-regional.up.railway.app"

# =========================
# INICIALIZACIÓN
# =========================
def inicializar_servidor():
    global INICIALIZADO
    if INICIALIZADO:
        return

    print("🚀 INICIANDO API TURISMO")
    print(f"🌐 BD Host: {os.environ.get('MYSQLHOST')}")
    print(f"🗄️  BD Name: {os.environ.get('MYSQLDATABASE')}")

    verificar_frontend_react()
    INICIALIZADO = True

# =========================
# BASE DE DATOS
# =========================
def conectar_base_datos():
    try:
        config = {
            "host": os.environ.get("MYSQLHOST"),
            "user": os.environ.get("MYSQLUSER"),
            "password": os.environ.get("MYSQLPASSWORD"),
            "database": os.environ.get("MYSQLDATABASE"),
            "port": int(os.environ.get("MYSQLPORT", 3306)),
            "connect_timeout": 10
        }

        if not config["host"] or not config["user"]:
            raise Exception("Variables de entorno MySQL incompletas")

        conexion = mysql.connector.connect(**config)
        return conexion

    except Error as e:
        raise Exception(f"Error BD: {str(e)}")

# =========================
# UTILIDADES
# =========================
def url_completa(ruta):
    if not ruta:
        return None

    base_url = obtener_base_url()
    ruta = ruta.replace("\\", "/").lstrip("/")

    if not ruta.startswith("assets/"):
        ruta = f"assets/{ruta}"

    return f"{base_url}/{ruta}"

def limpiar_columnas_absolutas(row):
    if not row:
        return {}

    limpio = {}
    for k, v in row.items():
        if v and any(x in k.lower() for x in ["ruta", "imagen", "icono", "foto", "logo"]):
            limpio[k] = url_completa(v)
        else:
            limpio[k] = v
    return limpio

# =========================
# MIDDLEWARE
# =========================
@app.before_request
def before_request():
    if not INICIALIZADO:
        inicializar_servidor()

# =========================
# FRONTEND REACT
# =========================
@app.route("/")
def index():
    if os.path.exists(os.path.join(DIST_PATH, "index.html")):
        return send_from_directory(DIST_PATH, "index.html")

    return jsonify({
        "status": "API OK",
        "mensaje": "Frontend no encontrado"
    })

@app.route("/<path:path>")
def react_router(path):
    archivo = os.path.join(DIST_PATH, path)
    if os.path.exists(archivo):
        return send_from_directory(DIST_PATH, path)

    return send_from_directory(DIST_PATH, "index.html")

# =========================
# API ENDPOINTS
# =========================
@app.route("/api/info-servidor")
def info_servidor():
    return jsonify({
        "status": "activo",
        "base_url": obtener_base_url(),
        "frontend": verificar_frontend_react()
    })

@app.route("/api/configuracion")
def configuracion():
    conn = conectar_base_datos()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM configuracion_app LIMIT 1")
    data = cur.fetchone()
    conn.close()
    return jsonify(limpiar_columnas_absolutas(data) if data else {})

@app.route("/api/regiones")
def regiones():
    conn = conectar_base_datos()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM regiones_zonas WHERE habilitar = 1 ORDER BY orden")
    rows = cur.fetchall()
    conn.close()
    return jsonify([limpiar_columnas_absolutas(r) for r in rows])

@app.route("/api/secciones")
def secciones():
    conn = conectar_base_datos()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM secciones WHERE habilitar = 1 ORDER BY orden")
    secciones = cur.fetchall()

    for s in secciones:
        cur.execute("""
            SELECT * FROM sub_secciones
            WHERE id_seccion = %s AND habilitar = 1
            ORDER BY orden
        """, (s["id_seccion"],))
        s["subsecciones"] = [
            limpiar_columnas_absolutas(x) for x in cur.fetchall()
        ]

    conn.close()
    return jsonify([limpiar_columnas_absolutas(s) for s in secciones])

# =========================
# ASSETS
# =========================
@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(ASSETS_PATH, filename)

# =========================
# ERRORES
# =========================
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint no encontrado"}), 404
    return send_from_directory(DIST_PATH, "index.html")

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
