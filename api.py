# api.py - PRODUCCIÓN FINAL RENDER + REACT (VITE) + FLASK
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
# FLASK APP
# =====================================================
app = Flask(
    __name__,
    static_folder="dist",
    static_url_path=""
)

# 🔐 SECRET KEY (SESIONES)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "turismo_secret_key"
)

# 🔐 CONFIG COOKIE PARA HTTPS (RENDER)
app.config.update(
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True
)

# 🌍 CORS CON CREDENCIALES
CORS(
    app,
    supports_credentials=True,
    origins="*"
)


# =====================================================
# LOG DE ARRANQUE (RENDER)
# =====================================================
print("===================================")
print("🚀 FLASK INICIADO")
print(f"📂 DIST_DIR: {DIST_DIR}")
print(f"📄 index.html existe: {os.path.exists(INDEX_FILE)}")
if os.path.exists(DIST_DIR):
    print("📁 Contenido dist/:", os.listdir(DIST_DIR))
print("===================================")

# =====================================================
# UTILIDADES
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
        if v and any(x in k.lower() for x in ["imagen", "foto", "icono", "logo", "ruta"]):
            salida[k] = url_completa(v)
        else:
            salida[k] = v
    return salida

# =====================================================
# CONEXIÓN BD
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
# FRONTEND (REACT)
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
# API
# =====================================================
@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "index": os.path.exists(INDEX_FILE)
    })

# ---------------- ADMIN - MANTENIMIENTO ------------------
# ⚠️ TEMPORAL — ejecutar una sola vez y luego eliminar

#@app.route("/admin/alter_visitas_app", methods=["POST"])
#def admin_alter_visitas_app():
#    try:
#        db = conectar_db()
#        cur = db.cursor()

#        # Verificar si ya existe la columna
#        cur.execute("""
#            SELECT COUNT(*)
#            FROM INFORMATION_SCHEMA.COLUMNS
#            WHERE TABLE_SCHEMA = DATABASE()
#              AND TABLE_NAME = 'configuracion_app'
#              AND COLUMN_NAME = 'visitas_app'
#        """)

#        existe = cur.fetchone()[0]

#        if existe == 0:
#            cur.execute("""
#                ALTER TABLE configuracion_app
#                ADD COLUMN visitas_app INT NOT NULL DEFAULT 0
#            """)
#            db.commit()
#            mensaje = "Columna visitas_app creada"
#        else:
#            mensaje = "La columna ya existe"

#        db.close()

#        return jsonify({
#            "ok": True,
#            "mensaje": mensaje
#        })

#    except Exception as e:
#        return jsonify({"error": str(e)}), 500




# ---------------- CONFIGURACIÓN APP ------------------

@app.route("/api/configuracion")
def configuracion():
    try:
        db = conectar_db()
        cur = db.cursor(dictionary=True)

        cur.execute("""
            SELECT
                id_config,
                titulo_app,
                logo_app_ruta_relativa,
                icono_hamburguesa_ruta_relativa,
                icono_cerrar_ruta_relativa,
                hero_titulo,
                hero_imagen_ruta_relativa,
                footer_texto,
                direccion_facebook,
                direccion_instagram,
                direccion_twitter,
                direccion_youtube,
                correo_electronico,
                visitas_app,
                habilitar
            FROM configuracion_app
            WHERE habilitar = 1
            ORDER BY id_config DESC
            LIMIT 1
        """)

        row = cur.fetchone()
        db.close()

        if not row:
            return jsonify({
                "status": "error",
                "message": "No hay configuración activa"
            }), 404

        return jsonify(normalizar_filas(row))

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------- REGIONES ------------------
@app.route("/api/regiones")
def regiones():
    try:
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

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------- ADMIN - MANTENIMIENTO ------------------
# ⚠️ TEMPORAL — ejecutar una sola vez y luego eliminar

@app.route("/admin/alter_subsecciones_likes", methods=["POST"])
def admin_alter_subsecciones_likes():
    try:
        db = conectar_db()
        cur = db.cursor()

        # verificar si ya existe la columna
        cur.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'sub_secciones'
              AND COLUMN_NAME = 'likes'
        """)

        existe = cur.fetchone()[0]

        if existe == 0:
            cur.execute("""
                ALTER TABLE sub_secciones
                ADD COLUMN likes INT NOT NULL DEFAULT 0
            """)
            db.commit()
            mensaje = "Columna likes creada en sub_secciones"
        else:
            mensaje = "La columna likes ya existe"

        db.close()

        return jsonify({
            "ok": True,
            "mensaje": mensaje
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------- SECCIONES ------------------
@app.route("/api/secciones")
def secciones():
    try:
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
                WHERE id_seccion = %s
                  AND habilitar = 1
                ORDER BY orden
            """, (s["id_seccion"],))
            s["subsecciones"] = [
                normalizar_filas(x) for x in cur.fetchall()
            ]

        db.close()
        return jsonify([normalizar_filas(s) for s in secciones])

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------- VISITAS APP ------------------
@app.route("/api/visita-app", methods=["POST"])
def registrar_visita_app():
    try:
        if session.get("visita_app_contada"):
            return jsonify({"status": "ok", "mensaje": "Visita ya contada"})

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

        return jsonify({"status": "ok", "mensaje": "Visita registrada"})

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
