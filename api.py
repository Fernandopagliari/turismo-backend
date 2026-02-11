# api.py — PRODUCCIÓN FINAL RENDER + VITE + FLASK

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
import mysql.connector
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

# ⚠️ IMPORTANTE — NO usar "*" con cookies
CORS(
    app,
    supports_credentials=True,
    origins=["https://turismo-backend-av60.onrender.com"]
)

# =====================================================
# LOG START
# =====================================================
print("===================================")
print("🚀 FLASK INICIADO")
print("DIST:", DIST_DIR)
print("INDEX existe:", os.path.exists(INDEX_FILE))
print("===================================")

# =====================================================
# UTIL
# =====================================================
def base_url():
    return request.url_root.rstrip("/")

def url_completa(ruta):
    if not ruta:
        return None
    ruta = ruta.replace("\\", "/").lstrip("/")
    if not ruta.startswith("assets/"):
        ruta = f"assets/{ruta}"
    return f"{base_url()}/{ruta}"

def normalizar_filas(row):
    salida = {}
    for k, v in row.items():
        if v and any(x in k.lower() for x in ["imagen","foto","icono","logo","ruta"]):
            salida[k] = url_completa(v)
        else:
            salida[k] = v
    return salida

# =====================================================
# DB
# =====================================================
def conectar_db():
    return mysql.connector.connect(
        host=os.environ.get("MYSQLHOST"),
        user=os.environ.get("MYSQLUSER"),
        password=os.environ.get("MYSQLPASSWORD"),
        database=os.environ.get("MYSQLDATABASE"),
        port=int(os.environ.get("MYSQLPORT", 3306)),
        connect_timeout=10
    )

# =====================================================
# API
# =====================================================

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


# ---------------- CONFIG ----------------

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

    return jsonify(normalizar_filas(row))


# ---------------- REGIONES ----------------

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


# ---------------- SECCIONES ----------------

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

    for s in secciones:
        cur.execute("""
            SELECT *
            FROM sub_secciones
            WHERE id_seccion=%s AND habilitar=1
            ORDER BY orden
        """, (s["id_seccion"],))
        s["subsecciones"] = [
            normalizar_filas(x) for x in cur.fetchall()
        ]

    db.close()
    return jsonify([normalizar_filas(s) for s in secciones])


# ---------------- VISITA APP ----------------

@app.route("/api/visita-app", methods=["POST"])
def visita_app():
    if session.get("visita_app_contada"):
        return jsonify({"ok": True})

    db = conectar_db()
    cur = db.cursor()

    cur.execute("""
        UPDATE configuracion_app
        SET visitas_app = visitas_app + 1
        WHERE id_config = (
            SELECT id_config FROM (
                SELECT id_config
                FROM configuracion_app
                WHERE habilitar = 1
                ORDER BY id_config DESC
                LIMIT 1
            ) t
        )
    """)

    db.commit()
    db.close()

    session["visita_app_contada"] = True
    return jsonify({"ok": True})


# ---------------- LIKES ----------------

@app.route("/api/subsecciones/<int:id_sub>/like", methods=["POST"])
def like_sub(id_sub):
    db = conectar_db()
    cur = db.cursor()

    # incrementar
    cur.execute("""
        UPDATE sub_secciones
        SET likes = likes + 1
        WHERE id_sub_seccion=%s
    """, (id_sub,))
    db.commit()

    # leer valor nuevo
    cur.execute("""
        SELECT likes
        FROM sub_secciones
        WHERE id_sub_seccion=%s
    """, (id_sub,))
    row = cur.fetchone()

    db.close()

    if not row:
        return jsonify({"error": "Subsección no encontrada"}), 404

    return jsonify({"likes": row[0]})



# =====================================================
# FRONTEND STATIC — AL FINAL
# =====================================================

@app.route("/")
def index():
    return send_from_directory(DIST_DIR, "index.html")

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
