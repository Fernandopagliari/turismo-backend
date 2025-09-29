# -*- coding: utf-8 -*-
import os
import sys
import time
import mysql.connector
from mysql.connector import Error
from PyQt5.QtWidgets import QMessageBox, QApplication, QProgressDialog, QInputDialog
import socket
import configparser

# Detecta la ruta correcta incluso dentro del .exe
def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

CONFIG_FILE = resource_path("config.ini")

# ---------------- CONFIGURACIÓN ----------------
def cargar_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if "mysql" in config:
            return config["mysql"]
    return None

def guardar_config(host, user, password, database, port=3306):
    config = configparser.ConfigParser()
    config["mysql"] = {
        "host": host,
        "user": user,
        "password": password,
        "database": database,
        "port": str(port)
    }
    with open(CONFIG_FILE, "w") as f:
        config.write(f)

# ---------------- CONEXIÓN ----------------
def conectar_base_datos(parent=None):
    try:
        datos = cargar_config()
        if datos:
            host = datos.get("host", "localhost")
            user = datos.get("user", "root")
            password = datos.get("password", "")
            database = datos.get("database", "databaseapp")
            port = int(datos.get("port", 3306))
        else:
            port = 3306
            database = "databaseapp"
            server_user = "root"
            server_password = "Perroponce@4472801"
            client_user = "usuario_remoto"
            client_password = "usuario123"

            host = "localhost"
            user = server_user
            password = server_password

            if socket.gethostname().lower() != "notebook":
                host = "192.168.0.104"
                user = client_user
                password = client_password

        conexion = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port
        )
        if conexion.is_connected() and not datos:
            guardar_config(host, user, password, database, port)
        return conexion

    except Error:
        # Solicitar datos manuales si falla la conexión automática
        if parent is None:
            parent = QApplication.activeWindow()
        QMessageBox.warning(parent, "Conexión Fallida",
                            "No se pudo conectar automáticamente. Se solicitarán los datos manualmente.")

        host, ok1 = QInputDialog.getText(parent, "Host", "Ingrese host de MySQL:", text="localhost")
        if not ok1: return None
        user, ok2 = QInputDialog.getText(parent, "Usuario", "Ingrese usuario:", text="root")
        if not ok2: return None
        password, ok3 = QInputDialog.getText(parent, "Contraseña", "Ingrese contraseña:", text="")
        if not ok3: return None
        database, ok4 = QInputDialog.getText(parent, "Base de datos", "Ingrese nombre de la base de datos:", text="databaseapp")
        if not ok4: return None

        try:
            conexion = mysql.connector.connect(
                host=host, user=user, password=password, database=database, port=3306
            )
            if conexion.is_connected():
                guardar_config(host, user, password, database, 3306)
                return conexion
        except Error as e2:
            QMessageBox.critical(parent, "Error de Conexión",
                                 f"No se pudo conectar a la base de datos con los datos ingresados:\n{e2}")
            return None

# ---------------- CERRAR ----------------
def cerrar_conexion(conexion):
    if conexion and conexion.is_connected():
        conexion.close()

# ---------------- INICIALIZACIÓN OPTIMIZADA ----------------
def inicializar_base_datos(parent=None):
    conexion = conectar_base_datos(parent)
    if not conexion:
        print("[ERROR] No se pudo conectar a la base de datos.")
        return

    pasos = [
        ("Creando tabla usuarios...", crear_tabla_usuarios),
        ("Creando tabla configuraciones...", crear_tabla_configuraciones),
        ("Creando tabla secciones...", crear_tabla_secciones),
        ("Creando tabla sub_secciones...", crear_tabla_sub_secciones),
        ("Creando tabla licencia...", crear_tabla_licencia),
        ("Insertando usuarios iniciales...", insert_initial_users),
    ]

    progreso = QProgressDialog("Inicializando base de datos...", "Cancelar", 0, len(pasos), parent)
    progreso.setWindowTitle("Inicialización")
    progreso.setMinimumDuration(2000)
    progreso.setValue(0)
    progreso.setAutoClose(True)
    progreso.setAutoReset(True)

    try:
        for i, (mensaje, funcion) in enumerate(pasos, start=1):
            if progreso.wasCanceled():
                break
            progreso.setLabelText(mensaje)
            QApplication.processEvents()
            try:
                funcion(conexion)
            except Exception as e:
                print(f"[ERROR] {mensaje}: {e}")
            progreso.setValue(i)
            QApplication.processEvents()
            time.sleep(0.2)
    finally:
        cerrar_conexion(conexion)

# ---------------- TABLAS ----------------
def crear_tabla_usuarios(conexion):
    cursor = conexion.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id_usuario INT AUTO_INCREMENT PRIMARY KEY,
                apellido_nombres_usuario VARCHAR(100),
                dni_usuario VARCHAR(20),
                domicilio_usuario VARCHAR(200),
                localidad_usuario VARCHAR(150),
                provincia_usuario VARCHAR(150),
                telefono_usuario VARCHAR(50),
                email_usuario VARCHAR(200),
                nombre_usuario_acceso VARCHAR(200) UNIQUE,
                password_usuario VARCHAR(150),
                foto_usuario VARCHAR(255),
                rol_usuario VARCHAR(200),
                activo INT NOT NULL DEFAULT 0
            )ENGINE=InnoDB;
        """)
    except Exception as e:
        print(f"Error al crear la tabla 'usuarios': {e}")
    finally:
        cursor.close()

def crear_tabla_configuraciones(conexion):
    cursor = conexion.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracion_app (
                id_config INT AUTO_INCREMENT PRIMARY KEY,
                titulo_app VARCHAR(100),
                logo_app VARCHAR(255) NOT NULL,
                logo_app_ruta_relativa VARCHAR(255) NOT NULL,
                icono_hamburguesa VARCHAR(255) DEFAULT NULL,
                icono_hamburguesa_ruta_relativa VARCHAR(255) DEFAULT NULL,
                icono_cerrar VARCHAR(255) DEFAULT NULL,
                icono_cerrar_ruta_relativa VARCHAR(255) DEFAULT NULL,
                hero_titulo VARCHAR(255) NOT NULL,
                hero_imagen VARCHAR(255),
                hero_imagen_ruta_relativa VARCHAR(255),
                footer_texto VARCHAR(255) NOT NULL,
                direccion_facebook VARCHAR(255),
                direccion_instagram VARCHAR(255),
                direccion_twitter VARCHAR(255),
                direccion_youtube VARCHAR(255),
                correo_electronico VARCHAR(255),
                habilitar BOOLEAN NOT NULL DEFAULT TRUE
            )ENGINE=InnoDB;
        """)
        conexion.commit()
    except Exception as e:
        print(f"Error al crear la tabla 'configuracion_app': {e}")
    finally:
        cursor.close()

def crear_tabla_regiones_zona(conexion):
    cursor = conexion.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS regiones_zonas ( 
            id_region_zona INT(11) AUTO_INCREMENT PRIMARY KEY,
            nombre_region_zona VARCHAR(100) NOT NULL,
            imagen_region_zona_ruta_relativa VARCHAR(255),
            habilitar BOOLEAN NOT NULL DEFAULT TRUE,
            orden INT NOT NULL DEFAULT 0
        ) ENGINE=InnoDB;
        """)
        conexion.commit()
    except Exception as e:
        print(f"Error al crear la tabla 'regiones_zona': {e}")
    finally:
        cursor.close()

def crear_tabla_secciones(conexion):
    cursor = conexion.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS secciones (
                id_seccion INT(11) AUTO_INCREMENT PRIMARY KEY,
                nombre_seccion VARCHAR(100) NOT NULL,
                icono_seccion VARCHAR(255),
                habilitar BOOLEAN NOT NULL DEFAULT TRUE,
                orden INT NOT NULL DEFAULT 0
            ) ENGINE=InnoDB;
        """)
        conexion.commit()
    except Exception as e:
        print(f"Error al crear la tabla 'secciones': {e}")
    finally:
        cursor.close()

def crear_tabla_sub_secciones(conexion):
    cursor = conexion.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sub_secciones (
                id_sub_seccion INT(11) AUTO_INCREMENT PRIMARY KEY,
                id_seccion INT(11) NOT NULL,
                id_region_zona INT(11) NOT NULL,
                nombre_sub_seccion VARCHAR(150) NOT NULL,
                domicilio VARCHAR(255),
                latitud DECIMAL(10,6),
                longitud DECIMAL(10,6),
                distancia VARCHAR(50),
                numero_telefono VARCHAR(30),
                imagen VARCHAR(255),
                imagen_ruta_relativa VARCHAR(255),
                icono VARCHAR(255),
                icono_ruta_relativa VARCHAR(255),
                itinerario_maps VARCHAR(500),
                habilitar BOOLEAN NOT NULL DEFAULT TRUE,
                fecha_desactivacion DATE NULL,
                orden INT(11) NOT NULL DEFAULT 0,
                destacado TINYINT DEFAULT 0,
                foto1_ruta_absoluta VARCHAR(255),
                foto1_ruta_relativa VARCHAR(255),
                foto2_ruta_absoluta VARCHAR(255),
                foto2_ruta_relativa VARCHAR(255),
                foto3_ruta_absoluta VARCHAR(255),
                foto3_ruta_relativa VARCHAR(255),
                foto4_ruta_absoluta VARCHAR(255),
                foto4_ruta_relativa VARCHAR(255),
                FOREIGN KEY (id_seccion) REFERENCES secciones(id_seccion) ON DELETE CASCADE,
                FOREIGN KEY (id_region_zona) REFERENCES regiones_zonas(id_region_zona) ON DELETE CASCADE
            ) ENGINE=InnoDB;
        """)
        conexion.commit()
    except Exception as e:
        print(f"Error al crear la tabla 'sub_secciones': {e}")
    finally:
        cursor.close()

def crear_tabla_licencia(conexion):
    cursor = conexion.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS licencia (
                id INT AUTO_INCREMENT PRIMARY KEY,
                serial VARCHAR(100) NOT NULL,
                clave VARCHAR(255) NOT NULL,
                fecha_activacion DATE NOT NULL,
                fecha_expiracion TEXT NOT NULL,
                hardware_id VARCHAR(255)
            ) ENGINE=InnoDB;
        """)
        conexion.commit()
    except Exception as e:
        print(f"Error al crear la tabla 'licencia': {e}")
    finally:
        cursor.close()

# ---------------- INSERTAR USUARIOS ----------------
def insert_initial_users(conexion):
    cursor = conexion.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.executemany("""
            INSERT INTO usuarios (apellido_nombres_usuario,nombre_usuario_acceso, email_usuario, password_usuario, rol_usuario, activo)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, [
            ("Admin Principal","admin", "admin@turismo.com", "admin123", "admin", 1),
            ("Editor Contenido", "editor", "editor@turismo.com", "editor123", "editor", 1),
            ("Usuario Prueba", "visor", "usuario@turismo.com", "usuario123", "visor", 1),
        ])
        conexion.commit()
    cursor.close()
