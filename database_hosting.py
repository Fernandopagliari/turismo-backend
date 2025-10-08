# database_hosting.py - EXCLUSIVO para base de datos del HOSTING
import mysql.connector
from mysql.connector import Error
from PyQt5.QtWidgets import QMessageBox
from database_local import obtener_configuracion_hosting  # ← NUEVA IMPORTACIÓN

def conectar_hosting(parent=None):
    """
    Conectar a la base de datos del hosting usando configuración de la tabla local
    """
    try:
        # Obtener configuración desde la DB local
        config = obtener_configuracion_hosting(parent)
        if not config:
            print("[ERROR] No se pudo obtener configuración del hosting desde DB local")
            return None
        
        print(f"[DEBUG] Conectando a hosting: {config['host']}:{config['port']}")
        
        conexion = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            port=config['port'],
            connect_timeout=30
        )
        
        if conexion.is_connected():
            print("[SUCCESS] Conexión a HOSTING exitosa")
            return conexion
            
    except Error as e:
        print(f"[ERROR] No se pudo conectar al hosting: {e}")
        
        # Mostrar error en PyQt5
        if parent is None:
            from PyQt5.QtWidgets import QApplication
            parent = QApplication.activeWindow()
        
        QMessageBox.warning(parent, "Conexión Fallida",
                           f"No se pudo conectar al servidor hosting:\n{e}\n\n"
                           f"Verifique que:\n"
                           f"- La configuración en 'datos_hosting' sea correcta\n"
                           f"- Su conexión a internet esté activa\n"
                           f"- El servidor hosting esté disponible")
        return None

def inicializar_base_datos_hosting(parent=None):
    """
    Inicializar todas las tablas de la aplicación en el hosting
    """
    conexion = conectar_hosting(parent)
    if not conexion:
        print("[ERROR] No se pudo conectar al hosting para inicialización")
        return False

    try:
        print("Inicializando base de datos del hosting...")
        
        # Lista de funciones para crear tablas
        funciones = [
            crear_tabla_configuraciones,
            crear_tabla_regiones_zona, 
            crear_tabla_secciones,
            crear_tabla_sub_secciones,
            crear_tabla_usuarios,
            verificar_y_agregar_campos_base64,
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
        print(f"[ERROR] Error durante inicialización del hosting: {e}")
        return False
    finally:
        cerrar_conexion(conexion)

# ... (el resto de las funciones se mantienen igual)
# -----------------Verificacion campos base64-------------------------
def verificar_y_agregar_campos_base64(conexion):
    """Verifica y agrega campos Base64 faltantes a todas las tablas en HOSTING"""
    try:
        cursor = conexion.cursor()
        
        # Lista de campos a verificar/agregar
        campos_por_tabla = {
            'configuracion_app': [
                'logo_base64 LONGTEXT',
                'icono_hamburguesa_base64 LONGTEXT', 
                'icono_cerrar_base64 LONGTEXT',
                'hero_imagen_base64 LONGTEXT'
            ],
            'regiones_zonas': ['imagen_region_zona_base64 LONGTEXT'],
            'usuarios': ['foto_usuario_base64 LONGTEXT'],
            'secciones': ['icono_seccion_base64 LONGTEXT'],
            'sub_secciones': [
                'imagen_base64 LONGTEXT',
                'icono_base64 LONGTEXT', 
                'foto1_base64 LONGTEXT',
                'foto2_base64 LONGTEXT',
                'foto3_base64 LONGTEXT',
                'foto4_base64 LONGTEXT'
            ]
        }
        
        for tabla, campos in campos_por_tabla.items():
            for campo in campos:
                try:
                    cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {campo}")
                    print(f"[OK] Campo {campo} agregado a {tabla}")
                except Exception as e:
                    print(f"[INFO] Campo {campo} ya existe en {tabla} o error: {e}")
        
        conexion.commit()
        cursor.close()
        print("[SUCCESS] Verificación de campos Base64 completada en HOSTING")
        
    except Exception as e:
        print(f"[ERROR] En verificación de campos Base64: {e}")

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
                foto_usuario_base64 LONGTEXT,
                rol_usuario VARCHAR(200),
                activo INT NOT NULL DEFAULT 0
            )ENGINE=InnoDB;
        """)
        print("[OK] Tabla 'usuarios' creada/verificada en HOSTING")
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
                logo_base64 LONGTEXT,  
                icono_hamburguesa VARCHAR(255) DEFAULT NULL,
                icono_hamburguesa_ruta_relativa VARCHAR(255) DEFAULT NULL,
                icono_hamburguesa_base64 LONGTEXT,
                icono_cerrar VARCHAR(255) DEFAULT NULL,
                icono_cerrar_ruta_relativa VARCHAR(255) DEFAULT NULL,
                icono_cerrar_base64 LONGTEXT,  
                hero_titulo VARCHAR(255) NOT NULL,
                hero_imagen VARCHAR(255),
                hero_imagen_ruta_relativa VARCHAR(255),
                hero_imagen_base64 LONGTEXT,  
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
        print("[OK] Tabla 'configuracion_app' creada/verificada en HOSTING")
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
                imagen_region_zona_base64 LONGTEXT,
                habilitar BOOLEAN NOT NULL DEFAULT TRUE,
                orden INT NOT NULL DEFAULT 0
            ) ENGINE=InnoDB;
        """)
        conexion.commit()
        print("[OK] Tabla 'regiones_zonas' creada/verificada en HOSTING")
    except Exception as e:
        print(f"Error al crear la tabla 'regiones_zonas': {e}")
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
                icono_seccion_base64 LONGTEXT,
                habilitar BOOLEAN NOT NULL DEFAULT TRUE,
                orden INT NOT NULL DEFAULT 0
            ) ENGINE=InnoDB;
        """)
        conexion.commit()
        print("[OK] Tabla 'secciones' creada/verificada en HOSTING")
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
                imagen_base64 LONGTEXT,
                icono VARCHAR(255),
                icono_ruta_relativa VARCHAR(255),
                icono_base64 LONGTEXT,
                itinerario_maps VARCHAR(500),
                habilitar BOOLEAN NOT NULL DEFAULT TRUE,
                fecha_desactivacion DATE NULL,
                orden INT(11) NOT NULL DEFAULT 0,
                destacado TINYINT DEFAULT 0,
                foto1_ruta_absoluta VARCHAR(255),
                foto1_ruta_relativa VARCHAR(255),
                foto1_base64 LONGTEXT,
                foto2_ruta_absoluta VARCHAR(255),
                foto2_ruta_relativa VARCHAR(255),
                foto2_base64 LONGTEXT,
                foto3_ruta_absoluta VARCHAR(255),
                foto3_ruta_relativa VARCHAR(255),
                foto3_base64 LONGTEXT,
                foto4_ruta_absoluta VARCHAR(255),
                foto4_ruta_relativa VARCHAR(255),
                foto4_base64 LONGTEXT,
                FOREIGN KEY (id_seccion) REFERENCES secciones(id_seccion) ON DELETE CASCADE,
                FOREIGN KEY (id_region_zona) REFERENCES regiones_zonas(id_region_zona) ON DELETE CASCADE
            ) ENGINE=InnoDB;
        """)
        conexion.commit()
        print("[OK] Tabla 'sub_secciones' creada/verificada en HOSTING")
    except Exception as e:
        print(f"Error al crear la tabla 'sub_secciones': {e}")
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
        print("[OK] Usuarios iniciales insertados en HOSTING")
    cursor.close()

def cerrar_conexion(conexion):
    """
    Cerrar conexión de forma segura
    """
    if conexion and conexion.is_connected():
        conexion.close()
        print("[OK] Conexión HOSTING cerrada")