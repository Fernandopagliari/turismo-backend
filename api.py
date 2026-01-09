# api.py - PRODUCCIÓN FINAL RENDER + REACT (VITE) + FLASK
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os

# =====================================================
# PATHS
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
INDEX_FILE = os.path.join(DIST_DIR, "index.html")

# =====================================================
# FLASK APP
# =====================================================
app = Flask(
    __name__,
    static_folder="dist",
    static_url_path=""
)

CORS(app)

# =====================================================
# LOG DE ARRANQUE (CLAVE PARA RENDER)
# =====================================================
print("===================================")
print("🚀 FLASK INICIADO")
print(f"📂 DIST_DIR: {DIST_DIR}")
print(f"📄 index.html existe: {os.path.exists(INDEX_FILE)}")
if os.path.exists(DIST_DIR):
   print("📁 Contenido dist/:", os.listdir(DIST_DIR))
print("===================================")


# =====================================================
# BASE URL DINÁMICA (IMÁGENES)
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
    if not row:
        return {}
    salida = {}
    for k, v in row.items():
        if v and any(x in k.lower() for x in ["imagen", "foto", "icono", "logo", "ruta"]):
            salida[k] = url_completa(v)
        else:
            salida[k] = v
    return salida


# =====================================================
# CONEXIÓN BD (RENDER)
# =====================================================
def conectar_db():
    try:
        return mysql.connector.connect(
            host=os.environ.get("MYSQLHOST"),
            user=os.environ.get("MYSQLUSER"),
            password=os.environ.get("MYSQLPASSWORD"),
            database=os.environ.get("MYSQLDATABASE"),
            port=int(os.environ.get("MYSQLPORT", 3306)),
            connect_timeout=10
        )
    except Error as e:
        raise Exception(str(e))


# =====================================================
# FRONTEND (REACT)
# =====================================================
@app.route("/")
def index():
    return send_from_directory(DIST_DIR, "index.html")


@app.route("/<path:path>")
def static_proxy(path):
    archivo = os.path.join(DIST_DIR, path)

    # Archivos reales (assets, css, js, imágenes)
    if os.path.exists(archivo):
        return send_from_directory(DIST_DIR, path)

    # Fallback React Router
    return send_from_directory(DIST_DIR, "index.html")


# =====================================================
# API
# =====================================================
@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "index": os.path.exists(INDEX_FILE)
    })

@app.route("/api/configuracion")
def configuracion():
    try:
        db = conectar_db()
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT * FROM configuracion_app
            WHERE habilitar = 1
            ORDER BY id_config DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        db.close()

        if not row:
            return jsonify({"error": "No hay configuración activa"}), 404

        return jsonify(normalizar_filas(row))

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/regiones")
def regiones():
    try:
        db = conectar_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM regiones_zonas WHERE habilitar = 1 ORDER BY orden")
        data = [normalizar_filas(r) for r in cur.fetchall()]
        db.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/secciones")
def secciones():
    try:
        db = conectar_db()
        cur = db.cursor(dictionary=True)

        cur.execute("SELECT * FROM secciones WHERE habilitar = 1 ORDER BY orden")
        secciones = cur.fetchall()

        for s in secciones:
            cur.execute(
                "SELECT * FROM sub_secciones WHERE id_seccion = %s AND habilitar = 1 ORDER BY orden",
                (s["id_seccion"],)
            )
            s["subsecciones"] = [
                normalizar_filas(x) for x in cur.fetchall()
            ]

        db.close()
        return jsonify([normalizar_filas(s) for s in secciones])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =====================================================
# ERRORES
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
