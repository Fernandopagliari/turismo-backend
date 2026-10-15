# api.py — PRODUCCIÓN OPTIMIZADO RENDER + VITE + FLASK

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

print("########################################")
print("API VERSION 04-08-2026 17:15")
print("########################################")


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


# =====================================================
# CONEXIÓN MYSQL — AIVEN / RENDER
# =====================================================
#
# Render NO utiliza la base de datos local "databaseapp".
#
# La aplicación publicada se conecta directamente
# a la base MySQL de Aiven mediante las variables
# de entorno configuradas en Render.
#
# Variables:
#
# MYSQLHOST
# MYSQLPORT
# MYSQLUSER
# MYSQLPASSWORD
# MYSQLDATABASE
#
# La contraseña NO se almacena en este archivo.
# =====================================================

MYSQL_HOST = os.environ.get("MYSQLHOST")
MYSQL_USER = os.environ.get("MYSQLUSER")
MYSQL_PASSWORD = os.environ.get("MYSQLPASSWORD")
MYSQL_DATABASE = os.environ.get("MYSQLDATABASE")

try:
    MYSQL_PORT = int(os.environ.get("MYSQLPORT", "3306"))
except (TypeError, ValueError):
    raise RuntimeError(
        "MYSQLPORT debe ser un número entero. "
        "Ejemplo: 17821"
    )


# =====================================================
# VALIDACIÓN DE CONFIGURACIÓN
# =====================================================

if not MYSQL_HOST:
    raise RuntimeError(
        "Falta la variable MYSQLHOST en Render."
    )

if not MYSQL_USER:
    raise RuntimeError(
        "Falta la variable MYSQLUSER en Render."
    )

if not MYSQL_PASSWORD:
    raise RuntimeError(
        "Falta la variable MYSQLPASSWORD en Render."
    )

if not MYSQL_DATABASE:
    raise RuntimeError(
        "Falta la variable MYSQLDATABASE en Render."
    )


# =====================================================
# INFORMACIÓN DE CONEXIÓN
# =====================================================

print("============== MYSQL AIVEN ==============")
print("HOST     =", MYSQL_HOST)
print("USER     =", MYSQL_USER)
print("DATABASE =", MYSQL_DATABASE)
print("PORT     =", MYSQL_PORT)
print("PASSWORD = ***")
print("==========================================")


# =====================================================
# VERSION MYSQL CONNECTOR
# =====================================================

print(
    "mysql.connector =",
    mysql.connector.__version__
)


# =====================================================
# DNS AIVEN
# =====================================================

try:

    print("Resolviendo DNS de Aiven...")

    ip = socket.gethostbyname(MYSQL_HOST)

    print("IP AIVEN =", ip)

except Exception as e:

    print(
        "ADVERTENCIA DNS =",
        repr(e)
    )


# =====================================================
# CONECTAR A AIVEN
# =====================================================

def conectar_db():
    """
    Crea una conexión directa con MySQL Aiven.

    No utiliza la base local databaseapp.
    No utiliza datos_hosting.
    No utiliza database_local.py.

    Render obtiene las credenciales directamente
    desde sus variables de entorno.
    """

    try:

        db = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            connection_timeout=15,
            use_pure=True
        )

        if not db.is_connected():

            raise mysql.connector.Error(
                "La conexión con Aiven no quedó establecida."
            )

        return db

    except mysql.connector.Error as e:

        print(
            "ERROR MYSQL AIVEN =",
            repr(e)
        )

        raise


# =====================================================
# UTIL
# =====================================================

def base_url():

    # fuerza https en render

    root = request.url_root.rstrip("/")

    if root.startswith("http://"):

        root = root.replace(
            "http://",
            "https://"
        )

    return root


def url_completa(ruta):

    if not ruta:
        return None

    ruta = str(ruta).replace(
        "\\",
        "/"
    )

    # URL completa

    if (
        ruta.startswith("http://")
        or
        ruta.startswith("https://")
    ):
        return ruta

    # Base64

    if ruta.startswith("data:"):

        return ruta

    # Ruta absoluta Windows

    if ":/" in ruta:

        partes = ruta.split(
            "/assets/",
            1
        )

        if len(partes) == 2:

            ruta = (
                "assets/"
                +
                partes[1]
            )

        else:

            return None

    ruta = ruta.lstrip("/")

    return (
        f"{base_url()}/{ruta}"
    )


def normalizar_filas(row):

    out = {}

    for k, v in row.items():

        if not v:

            out[k] = v

            continue

        # SOLO convertir rutas relativas

        if k.endswith(
            "_ruta_relativa"
        ):

            out[k] = url_completa(v)

        else:

            out[k] = v

    return out


# =====================================================
# HEALTH
# =====================================================

@app.route("/api/health")
def health():

    return jsonify(
        {
            "status": "ok"
        }
    )


# =====================================================
# CONFIGURACION (cacheable)
# =====================================================

@app.route("/api/configuracion")
def configuracion():

    db = conectar_db()

    cur = db.cursor(
        dictionary=True
    )

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

        return jsonify(
            {
                "error":
                "Sin configuración"
            }
        ), 404

    row["logo_app"] = (
        row[
            "logo_app_ruta_relativa"
        ]
    )

    row["icono_hamburguesa"] = (
        row[
            "icono_hamburguesa_ruta_relativa"
        ]
    )

    row["icono_cerrar"] = (
        row[
            "icono_cerrar_ruta_relativa"
        ]
    )

    row["hero_imagen"] = (
        row[
            "hero_imagen_ruta_relativa"
        ]
    )

    resp = jsonify(
        normalizar_filas(row)
    )

    resp.headers[
        "Cache-Control"
    ] = "public, max-age=30"

    return resp


# =====================================================
# REGIONES
# =====================================================

@app.route("/api/regiones")
def regiones():

    db = conectar_db()

    cur = db.cursor(
        dictionary=True
    )

    cur.execute("""
        SELECT *
        FROM regiones_zonas
        WHERE habilitar = 1
        ORDER BY orden
    """)

    data = [
        normalizar_filas(r)
        for r in cur.fetchall()
    ]

    db.close()

    return jsonify(data)


# =====================================================
# SECCIONES + SUBSECCIONES
# =====================================================

@app.route("/api/secciones")
def secciones():

    db = conectar_db()

    cur = db.cursor(
        dictionary=True
    )

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

    # agrupar en memoria

    subs_por_seccion = {}

    for s in subs:

        sid = s[
            "id_seccion"
        ]

        subs_por_seccion.setdefault(
            sid,
            []
        ).append(
            normalizar_filas(s)
        )

    for s in secciones:

        s["subsecciones"] = (
            subs_por_seccion.get(
                s["id_seccion"],
                []
            )
        )

    return jsonify(
        [
            normalizar_filas(s)
            for s in secciones
        ]
    )


# =====================================================
# VISITA APP
# =====================================================

@app.route(
    "/api/visita-app",
    methods=["POST"]
)
def visita_app():

    if session.get(
        "visita_app_contada"
    ):

        return jsonify(
            {
                "ok": True
            }
        )

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

    session[
        "visita_app_contada"
    ] = True

    return jsonify(
        {
            "ok": True
        }
    )


# =====================================================
# SOLO CONTADOR VISITAS
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

    return jsonify(
        {
            "visitas":
            row[0]
            if row
            else 0
        }
    )


# =====================================================
# LIKES
# =====================================================

@app.route(
    "/api/subsecciones/<int:id_sub>/like",
    methods=["POST"]
)
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

        return jsonify(
            {
                "error":
                "No encontrada"
            }
        ), 404

    return jsonify(
        {
            "likes":
            row[0]
        }
    )


# =====================================================
# STATIC (cache fuerte)
# =====================================================

@app.route("/")
def index():

    return send_from_directory(
        DIST_DIR,
        "index.html"
    )


@app.route(
    "/assets/<path:filename>"
)
def assets(filename):

    resp = send_from_directory(
        os.path.join(
            DIST_DIR,
            "assets"
        ),
        filename
    )

    resp.headers[
        "Cache-Control"
    ] = "public, max-age=31536000"

    return resp


@app.route(
    "/<path:path>"
)
def static_proxy(path):

    archivo = os.path.join(
        DIST_DIR,
        path
    )

    if os.path.exists(archivo):

        return send_from_directory(
            DIST_DIR,
            path
        )

    return send_from_directory(
        DIST_DIR,
        "index.html"
    )


# =====================================================
# API 404
# =====================================================

@app.errorhandler(404)
def not_found(e):

    if request.path.startswith(
        "/api"
    ):

        return jsonify(
            {
                "error":
                "API no encontrada"
            }
        ), 404

    return send_from_directory(
        DIST_DIR,
        "index.html"
    )


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )