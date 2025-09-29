# database.py - VERSIÓN PARA RAILWAY
import os
import mysql.connector
from mysql.connector import Error

def conectar_base_datos():
    """
    Conexión simplificada para Railway - usa variables de entorno
    """
    try:
        # Railway provee estas variables automáticamente
        host = os.environ.get('MYSQLHOST', 'localhost')
        user = os.environ.get('MYSQLUSER', 'root')
        password = os.environ.get('MYSQLPASSWORD', '')
        database = os.environ.get('MYSQLDATABASE', 'railway')  # ¡CAMBIADO A 'railway'!
        port = int(os.environ.get('MYSQLPORT', '3306'))

        print(f"[DEBUG] Conectando a MySQL: {host}:{port}")
        
        conexion = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            connect_timeout=30
        )
        
        if conexion.is_connected():
            print("[SUCCESS] Conexión a MySQL exitosa")
            return conexion
            
    except Error as e:
        print(f"[ERROR] No se pudo conectar a MySQL: {e}")
        return None

def cerrar_conexion(conexion):
    if conexion and conexion.is_connected():
        conexion.close()

# ---------------- INICIALIZACIÓN SIMPLIFICADA ----------------
def inicializar_base_datos():
    """Versión simplificada sin PyQt5 para Railway"""
    conexion = conectar_base_datos()
    if not conexion:
        print("[ERROR] No se pudo conectar a la base de datos.")
        return False

    try:
        print("Inicializando base de datos...")
        
        # Solo las tablas esenciales
        funciones = [
            crear_tabla_configuraciones,
            crear_tabla_regiones_zona, 
            crear_tabla_secciones,
            crear_tabla_sub_secciones,
            insert_initial_users
        ]
        
        for funcion in funciones:
            try:
                funcion(conexion)
                print(f"[OK] {funcion.__name__} completada")
            except Exception as e:
                print(f"[ERROR] en {funcion.__name__}: {e}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error durante inicialización: {e}")
        return False
    finally:
        cerrar_conexion(conexion)

# ---------------- TABLAS (MANTENER IGUAL) ----------------
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
        print("[OK] Tabla configuracion_app creada/verificada")
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
        print("[OK] Tabla regiones_zonas creada/verificada")
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
        print("[OK] Tabla secciones creada/verificada")
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
        print("[OK] Tabla sub_secciones creada/verificada")
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
        print("[OK] Tabla licencia creada/verificada")
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
        print("[OK] Usuarios iniciales insertados")
    cursor.close()