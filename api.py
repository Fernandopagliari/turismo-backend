# api.py — PRODUCCIÓN OPTIMIZADO RENDER + VITE + FLASK

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
import os

# =====================================================
# PATHS
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
INDEX_FILE = os.path.join(DIST_DIR, "index.html")

# =====================================================
# APP
# =====================================================
app = Flask(__name__, static_folder="dist", static_url_path="")

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "turismo_secret_key")

app.config.update(
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True
)

CORS(
    app,
    supports_credentials=True,
    origins=["https://turismo-backend-av60.onrender.com"]
)

print("===================================")
print("🚀 FLASK INICIADO")
print("DIST:", DIST_DIR)
print("INDEX existe:", os.path.exists(INDEX_FILE))
print("===================================")

import socket

print("============== VARIABLES ==============")
print("HOST =", repr(os.environ.get("MYSQLHOST")))
print("USER =", repr(os.environ.get("MYSQLUSER")))
print("DATABASE =", repr(os.environ.get("MYSQLDATABASE")))
print("PORT =", repr(os.environ.get("MYSQLPORT")))
print("PASSWORD =", "***" if os.environ.get("MYSQLPASSWORD") else None)
print("=======================================")

print("mysql.connector =", mysql.connector.__version__)

try:
    print("Resolviendo DNS...")
    ip = socket.gethostbyname(os.environ.get("MYSQLHOST"))
    print("IP =", ip)
except Exception as e:
    print("ERROR DNS =", repr(e))
# =====================================================
# DB POOL (🔥 mejora fuerte de rendimiento)
# =====================================================
db_pool = pooling.MySQLConnectionPool(
    pool_name="turismo_pool",
    pool_size=5,
    host=os.environ.get("MYSQLHOST"),
    user=os.environ.get("MYSQLUSER"),
    password=os.environ.get("MYSQLPASSWORD"),
    database=os.environ.get("MYSQLDATABASE"),
    port=int(os.environ.get("MYSQLPORT", 3306)),
    connect_timeout=10
)


def conectar_db():
    return db_pool.get_connection()

# =====================================================
# UTIL
# =====================================================
def base_url():
    # fuerza https en render
    root = request.url_root.rstrip("/")
    if root.startswith("http://"):
        root = root.replace("http://", "https://")
    return root

def url_completa(ruta):
    if not ruta:
        return None
    ruta = ruta.replace("\\", "/").lstrip("/")
    if not ruta.startswith("assets/"):
        ruta = f"assets/{ruta}"
    return f"{base_url()}/{ruta}"

def normalizar_filas(row):
    out = {}
    for k, v in row.items():
        if v and any(x in k.lower() for x in ["imagen","foto","icono","logo","ruta"]):
            out[k] = url_completa(v)
        else:
            out[k] = v
    return out

# =====================================================
# HEALTH
# =====================================================
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


# =====================================================
# CONFIGURACION (cacheable)
# =====================================================
@app.route("/api/configuracion")
def configuracion():
    db = conectar_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT *
        FROM configuracion_app
        WHERE habilitar = 1
        ORDER BY id_config DESC
        LIMIT 1
    """)

    row = cur.fetchone()
    db.close()

    if not row:
        return jsonify({"error": "Sin configuración"}), 404

    resp = jsonify(normalizar_filas(row))
    resp.headers["Cache-Control"] = "public, max-age=30"
    return resp


# =====================================================
# REGIONES
# =====================================================
@app.route("/api/regiones")
def regiones():
    db = conectar_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT *
        FROM regiones_zonas
        WHERE habilitar = 1
        ORDER BY orden
    """)

    data = [normalizar_filas(r) for r in cur.fetchall()]
    db.close()
    return jsonify(data)


# =====================================================
# SECCIONES + SUBSECCIONES (🔥 sin N+1 queries)
# =====================================================
@app.route("/api/secciones")
def secciones():
    db = conectar_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT *
        FROM secciones
        WHERE habilitar = 1
        ORDER BY orden
    """)
    secciones = cur.fetchall()

    cur.execute("""
        SELECT *
        FROM sub_secciones
        WHERE habilitar = 1
        ORDER BY orden
    """)
    subs = cur.fetchall()
    db.close()

    # agrupar en memoria (🔥 evita query por sección)
    subs_por_seccion = {}
    for s in subs:
        sid = s["id_seccion"]
        subs_por_seccion.setdefault(sid, []).append(normalizar_filas(s))

    for s in secciones:
        s["subsecciones"] = subs_por_seccion.get(s["id_seccion"], [])

    return jsonify([normalizar_filas(s) for s in secciones])


# =====================================================
# VISITA APP (ultra rápido)
# =====================================================
@app.route("/api/visita-app", methods=["POST"])
def visita_app():

    if session.get("visita_app_contada"):
        return jsonify({"ok": True})

    db = conectar_db()
    cur = db.cursor()

    cur.execute("""
        UPDATE configuracion_app
        SET visitas_app = visitas_app + 1
        WHERE habilitar = 1
        ORDER BY id_config DESC
        LIMIT 1
    """)

    db.commit()
    db.close()

    session["visita_app_contada"] = True
    return jsonify({"ok": True})


# =====================================================
# SOLO CONTADOR VISITAS (🔥 endpoint liviano live)
# =====================================================
@app.route("/api/visitas")
def visitas_live():
    db = conectar_db()
    cur = db.cursor()

    cur.execute("""
        SELECT visitas_app
        FROM configuracion_app
        WHERE habilitar = 1
        ORDER BY id_config DESC
        LIMIT 1
    """)

    row = cur.fetchone()
    db.close()

    return jsonify({"visitas": row[0] if row else 0})


# =====================================================
# LIKES
# =====================================================
@app.route("/api/subsecciones/<int:id_sub>/like", methods=["POST"])
def like_sub(id_sub):

    db = conectar_db()
    cur = db.cursor()

    cur.execute("""
        UPDATE sub_secciones
        SET likes = likes + 1
        WHERE id_sub_seccion=%s
    """, (id_sub,))
    db.commit()

    cur.execute("""
        SELECT likes
        FROM sub_secciones
        WHERE id_sub_seccion=%s
    """, (id_sub,))
    row = cur.fetchone()

    db.close()

    if not row:
        return jsonify({"error": "No encontrada"}), 404

    return jsonify({"likes": row[0]})


# =====================================================
# STATIC (cache fuerte)
# =====================================================
@app.route("/")
def index():
    return send_from_directory(DIST_DIR, "index.html")

@app.route("/assets/<path:filename>")
def assets(filename):
    resp = send_from_directory(os.path.join(DIST_DIR, "assets"), filename)
    resp.headers["Cache-Control"] = "public, max-age=31536000"
    return resp

@app.route("/<path:path>")
def static_proxy(path):
    archivo = os.path.join(DIST_DIR, path)
    if os.path.exists(archivo):
        return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, "index.html")


# =====================================================
# API 404
# =====================================================
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api"):
        return jsonify({"error": "API no encontrada"}), 404
    return send_from_directory(DIST_DIR, "index.html")


# =====================================================
# MAIN
# =====================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
