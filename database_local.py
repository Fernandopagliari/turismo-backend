# database_local.py - EXCLUSIVO para base de datos LOCAL
import mysql.connector
from mysql.connector import Error
from PyQt5.QtWidgets import QMessageBox, QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt
import sys
import json
import os

# ✅ VARIABLE GLOBAL TEMPORAL solo para primera instalación
CREDENCIALES_LOCALES_TEMPORALES = None
CONFIG_FILE = "mysql_config.json"

class DialogoCredencialesMySQL(QDialog):
    """Diálogo para ingresar credenciales de MySQL local - CONEXIÓN LOCAL"""
    def __init__(self, parent=None, titulo_personalizado=None, es_reconfiguracion=False):
        super().__init__(parent)
        
        if titulo_personalizado:
            self.setWindowTitle(titulo_personalizado)
        else:
            if es_reconfiguracion:
                self.setWindowTitle("🔧 Reconfigurar MySQL Local")
            else:
                self.setWindowTitle("🔧 Configuración MySQL Local - Primera Instalación")
            
        self.setFixedSize(450, 420)  # ✅ Aumentado para base_url
        self.setWindowModality(Qt.ApplicationModal)
        
        layout = QVBoxLayout()
        
        # Título más descriptivo para CONEXIÓN LOCAL
        if es_reconfiguracion:
            titulo = QLabel("⚙️ RECONFIGURAR CONEXIÓN LOCAL")
            descripcion_texto = (
                "📋 Se detectó que la configuración local actual no funciona.\n"
                "Por favor, ingrese las nuevas credenciales de MySQL LOCAL.\n\n"
                "🔐 Ingrese los datos de conexión corregidos:"
            )
        else:
            titulo = QLabel("⚙️ CONFIGURACIÓN INICIAL - MySQL Local")
            descripcion_texto = (
                "📋 Primera instalación: Se necesitan credenciales de MySQL LOCAL\n"
                "para crear la base de datos 'databaseapp'.\n\n"
                "🔐 Ingrese los datos de conexión de su servidor MySQL LOCAL:"
            )
        
        titulo.setStyleSheet("font-weight: bold; font-size: 13px; color: #2c3e50; background-color: #ecf0f1; padding: 6px; border-radius: 3px;")
        layout.addWidget(titulo)
        
        descripcion = QLabel(descripcion_texto)
        descripcion.setWordWrap(True)
        descripcion.setStyleSheet("color: #7f8c8d; margin-bottom: 10px; padding: 3px; font-size: 11px;")
        layout.addWidget(descripcion)
        
        # Campos con padding reducido
        layout.addWidget(QLabel("🌐 Host del servidor:"))
        self.host_input = QLineEdit()
        self.host_input.setText("localhost")
        self.host_input.setPlaceholderText("localhost, 127.0.0.1")
        self.host_input.setStyleSheet("padding: 4px; font-size: 11px; border: 1px solid #bdc3c7; border-radius: 2px;")
        layout.addWidget(self.host_input)
        
        layout.addWidget(QLabel("👤 Usuario:"))
        self.usuario_input = QLineEdit()
        self.usuario_input.setText("root")
        self.usuario_input.setPlaceholderText("Usuario MySQL")
        self.usuario_input.setStyleSheet("padding: 4px; font-size: 11px; border: 1px solid #bdc3c7; border-radius: 2px;")
        layout.addWidget(self.usuario_input)
        
        layout.addWidget(QLabel("🔑 Contraseña:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Contraseña MySQL (puede estar vacía)")
        self.password_input.setStyleSheet("padding: 4px; font-size: 11px; border: 1px solid #bdc3c7; border-radius: 2px;")
        layout.addWidget(self.password_input)
        
        layout.addWidget(QLabel("🔌 Puerto:"))
        self.puerto_input = QLineEdit()
        self.puerto_input.setText("3306")
        self.puerto_input.setPlaceholderText("3306")
        self.puerto_input.setStyleSheet("padding: 4px; font-size: 11px; border: 1px solid #bdc3c7; border-radius: 2px;")
        layout.addWidget(self.puerto_input)
        
        # ✅ NUEVO CAMPO: Base URL
        layout.addWidget(QLabel("🌐 Base URL (API):"))
        self.base_url_input = QLineEdit()
        self.base_url_input.setText("http://localhost:5000")
        self.base_url_input.setPlaceholderText("http://localhost:5000 o https://tudominio.com")
        self.base_url_input.setStyleSheet("padding: 4px; font-size: 11px; border: 1px solid #bdc3c7; border-radius: 2px;")
        layout.addWidget(self.base_url_input)
        
        # Espaciador
        layout.addSpacing(10)
        
        # Botones con padding reducido
        botones_layout = QHBoxLayout()
        
        self.btn_probar = QPushButton("🔍 Probar Conexión")
        self.btn_probar.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 6px 10px;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.btn_probar.clicked.connect(self.probar_conexion)
        botones_layout.addWidget(self.btn_probar)
        
        self.btn_aceptar = QPushButton("💾 Aceptar")
        self.btn_aceptar.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
        """)
        self.btn_aceptar.clicked.connect(self.aceptar)
        botones_layout.addWidget(self.btn_aceptar)
        
        self.btn_cancelar = QPushButton("❌ Cancelar")
        self.btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.btn_cancelar.clicked.connect(self.reject)
        botones_layout.addWidget(self.btn_cancelar)
        
        layout.addLayout(botones_layout)
        
        # Información adicional
        info = QLabel(
            "💡 Las credenciales se guardarán en la tabla 'datos_host_local'\n"
            "para uso futuro. Base URL es para la API del frontend."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #95a5a6; font-size: 10px; margin-top: 8px; padding: 6px; background-color: #f8f9fa; border-radius: 3px;")
        layout.addWidget(info)
        
        self.setLayout(layout)
        
        self.credenciales = None
        self.es_reconfiguracion = es_reconfiguracion
    
    def probar_conexion(self):
        """Probar la conexión LOCAL con las credenciales ingresadas"""
        host = self.host_input.text().strip()
        usuario = self.usuario_input.text().strip()
        password = self.password_input.text()
        puerto = self.puerto_input.text().strip()
        
        if not host:
            QMessageBox.warning(self, "Campo requerido", "El campo 'Host' es obligatorio.")
            return False
            
        if not usuario:
            QMessageBox.warning(self, "Campo requerido", "El campo 'Usuario' es obligatorio.")
            return False
            
        if not puerto.isdigit():
            QMessageBox.warning(self, "Error", "El puerto debe ser un número válido.")
            return False
        
        try:
            # ✅ FILTRAR parámetros válidos para MySQL
            parametros_conexion = {
                'host': host,
                'user': usuario,
                'password': password,
                'port': int(puerto),
                'connect_timeout': 8
            }
            conexion = mysql.connector.connect(**parametros_conexion)
            
            if conexion.is_connected():
                info_servidor = conexion.get_server_info()
                conexion.close()
                
                if self.es_reconfiguracion:
                    mensaje = f"✅ Conexión LOCAL restaurada correctamente!\n\nServidor: {info_servidor}\nHost: {host}\nUsuario: {usuario}"
                else:
                    mensaje = f"✅ Conexión LOCAL exitosa!\n\nServidor: {info_servidor}\nHost: {host}\nUsuario: {usuario}"
                
                QMessageBox.information(self, "Conexión Exitosa", mensaje)
                return True
                
        except Error as e:
            QMessageBox.critical(self, "Error de Conexión", 
                               f"No se pudo conectar a MySQL LOCAL:\n\nError: {str(e)}\n\nVerifique las credenciales e intente nuevamente.")
            return False
    
    def aceptar(self):
        """Aceptar las credenciales LOCALES si la conexión es exitosa"""
        if self.probar_conexion():
            self.credenciales = {
                'host': self.host_input.text().strip(),
                'user': self.usuario_input.text().strip(),
                'password': self.password_input.text(),
                'port': int(self.puerto_input.text().strip()),
                'base_url': self.base_url_input.text().strip()  # ✅ NUEVO CAMPO
            }
            self.accept()

def obtener_credenciales_mysql(parent=None, es_reconfiguracion=False):
    """Obtener credenciales de MySQL LOCAL mediante diálogo"""
    try:
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        
        if es_reconfiguracion:
            titulo = "🔧 Reconfigurar MySQL Local"
        else:
            titulo = "🔧 Configuración MySQL Local - Primera Instalación"
        
        dialogo = DialogoCredencialesMySQL(parent, titulo, es_reconfiguracion)
        if dialogo.exec_() == QDialog.Accepted:
            return dialogo.credenciales
        else:
            if es_reconfiguracion:
                QMessageBox.warning(parent, "Reconfiguración Cancelada", "La aplicación no puede continuar sin una conexión LOCAL válida.")
            else:
                QMessageBox.warning(parent, "Instalación Cancelada", "La aplicación no puede continuar sin acceso a MySQL LOCAL.")
            return None
    except Exception as e:
        print(f"Error al mostrar diálogo de credenciales LOCALES: {e}")
        return None

def guardar_configuracion_externa(credenciales):
    """Guardar configuración en archivo externo para recuperación rápida"""
    try:
        config = {
            'host': credenciales['host'],
            'user': credenciales['user'],
            'password': credenciales['password'],
            'port': credenciales['port'],
            'database': 'databaseapp',
            'base_url': credenciales.get('base_url', 'http://localhost:5000')  # ✅ NUEVO
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"[SUCCESS] 💾 Configuración guardada en {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"[ERROR] ❌ No se pudo guardar configuración externa: {e}")
        return False

def cargar_configuracion_externa():
    """Cargar configuración desde archivo externo"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            print(f"[SUCCESS] 📂 Configuración cargada desde {CONFIG_FILE}")
            return config
        return None
    except Exception as e:
        print(f"[ERROR] ❌ No se pudo cargar configuración externa: {e}")
        return None

def crear_tabla_licencia(conexion):
    """Crear tabla de licencia en DB local"""
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
        print("[OK] Tabla 'licencia' creada/verificada")
    except Exception as e:
        print(f"Error al crear tabla 'licencia': {e}")
    finally:
        cursor.close()

def crear_tabla_datos_host_local(conexion):
    """Crear tabla para configuración de conexión LOCAL"""
    cursor = conexion.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS datos_host_local (
                id INT AUTO_INCREMENT PRIMARY KEY,
                host VARCHAR(255) NOT NULL,
                usuario VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                base_datos VARCHAR(255) NOT NULL,
                puerto INT NOT NULL DEFAULT 3306,
                base_url VARCHAR(255) NULL,
                activo BOOLEAN NOT NULL DEFAULT TRUE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
        """)
        
        conexion.commit()
        print("[OK] Tabla 'datos_host_local' creada/verificada")
        
    except Exception as e:
        print(f"Error al crear tabla 'datos_host_local': {e}")
    finally:
        cursor.close()

def crear_tabla_datos_hosting(conexion):
    """Crear tabla para configuración de conexión al SERVIDOR REMOTO"""
    cursor = conexion.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS datos_hosting (
                id INT AUTO_INCREMENT PRIMARY KEY,
                host VARCHAR(255) NOT NULL,
                usuario VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                base_datos VARCHAR(255) NOT NULL,
                puerto INT NOT NULL DEFAULT 3306,
                base_url VARCHAR(255) NULL,
                activo BOOLEAN NOT NULL DEFAULT TRUE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
        """)
        
        conexion.commit()
        print("[OK] Tabla 'datos_hosting' creada/verificada")
        
    except Exception as e:
        print(f"Error al crear tabla 'datos_hosting': {e}")
    finally:
        cursor.close()

def conectar_y_guardar_configuracion(credenciales, parent=None):
    """
    Conectar con credenciales y guardarlas en tabla Y archivo externo
    """
    global CREDENCIALES_LOCALES_TEMPORALES
    
    print(f"[DEBUG] 🛠️ Conectando y guardando: {credenciales['user']}@{credenciales['host']}")
    
    try:
        # ✅ GUARDAR como temporales inmediatamente
        CREDENCIALES_LOCALES_TEMPORALES = credenciales.copy()
        
        # Primero conectar sin base de datos para crearla
        print("[DEBUG] Conectando sin base de datos...")
        # ✅ FILTRAR parámetros válidos para MySQL
        parametros_conexion = {k: v for k, v in credenciales.items() 
                             if k in ['host', 'user', 'password', 'port']}
        conexion = mysql.connector.connect(**parametros_conexion, connect_timeout=5)
        
        cursor = conexion.cursor()
        print("[DEBUG] Creando base de datos si no existe...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS databaseapp")
        
        # Ahora conectar a la base de datos específica
        print("[DEBUG] Conectando a databaseapp...")
        parametros_con_db = parametros_conexion.copy()
        parametros_con_db['database'] = "databaseapp"
        conexion_db = mysql.connector.connect(**parametros_con_db, connect_timeout=5)
        
        # Crear tablas si no existen
        print("[DEBUG] Creando/verificando tablas...")
        crear_tabla_licencia(conexion_db)
        crear_tabla_datos_host_local(conexion_db)
        crear_tabla_datos_hosting(conexion_db)
        
        # ✅ GUARDAR en tabla datos_host_local
        print("[DEBUG] Guardando en tabla datos_host_local...")
        cursor_db = conexion_db.cursor()
        
        # Limpiar configuraciones anteriores
        cursor_db.execute("UPDATE datos_host_local SET activo = 0")
        
        # Insertar nueva configuración
        cursor_db.execute("""
            INSERT INTO datos_host_local (host, usuario, password, base_datos, puerto, base_url, activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            credenciales['host'],
            credenciales['user'],
            credenciales['password'],
            "databaseapp",
            credenciales['port'],
            credenciales.get('base_url', 'http://localhost:5000'),  # ✅ NUEVO
            True
        ))
        
        conexion_db.commit()
        
        # ✅ GUARDAR en archivo externo
        print("[DEBUG] Guardando en archivo externo...")
        guardar_configuracion_externa(credenciales)
        
        # VERIFICAR que se guardó correctamente
        cursor_db.execute("SELECT host, usuario, base_url FROM datos_host_local WHERE activo = 1")
        verificacion = cursor_db.fetchone()
        if verificacion:
            print(f"[DEBUG] ✅ Verificación: guardado correctamente - {verificacion[1]}@{verificacion[0]} - URL: {verificacion[2]}")
        else:
            print("[DEBUG] ❌ Verificación: NO se pudo verificar el guardado")
        
        cursor.close()
        conexion.close()
        cursor_db.close()
        conexion_db.close()
        
        print(f"[SUCCESS] ✅ Configuración LOCAL guardada en tabla y archivo: {credenciales['user']}@{credenciales['host']}")
        return True
        
    except Error as e:
        print(f"[ERROR] ❌ No se pudo guardar configuración: {e}")
        return False

def obtener_configuracion_automatica():
    """
    Obtener configuración automáticamente (archivo externo -> tabla)
    """
    print("\n[DEBUG] 🔍 BUSCANDO CONFIGURACIÓN AUTOMÁTICA")
    
    # 1. PRIMERO: Buscar en archivo externo
    print("[DEBUG] 1. Buscando en archivo externo...")
    config_externa = cargar_configuracion_externa()
    
    if config_externa:
        print(f"[DEBUG] ✅ Configuración externa encontrada: {config_externa['user']}@{config_externa['host']}")
        try:
            # ✅ FILTRAR parámetros válidos para MySQL
            parametros_conexion = {k: v for k, v in config_externa.items() 
                                 if k in ['host', 'user', 'password', 'database', 'port']}
            conexion = mysql.connector.connect(**parametros_conexion, connect_timeout=5)
            if conexion.is_connected():
                print("[SUCCESS] ✅ Conexión desde archivo externo EXITOSA")
                conexion.close()
                return config_externa
        except Error as e:
            print(f"[DEBUG] ❌ Configuración externa no funciona: {e}")
    
    # 2. SEGUNDO: Intentar leer de la tabla con métodos alternativos
    print("[DEBUG] 2. Intentando leer de tabla...")
    
    configuraciones_prueba = [
        {'host': "localhost", 'user': "root", 'password': "", 'database': "databaseapp", 'port': 3306, 'base_url': "http://localhost:5000"},
        {'host': "localhost", 'user': "root", 'password': "root", 'database': "databaseapp", 'port': 3306, 'base_url': "http://localhost:5000"},
        {'host': "127.0.0.1", 'user': "root", 'password': "", 'database': "databaseapp", 'port': 3306, 'base_url': "http://localhost:5000"},
    ]
    
    for config in configuraciones_prueba:
        try:
            print(f"[DEBUG] 🔄 Probando: {config['user']}@{config['host']}")
            # ✅ FILTRAR parámetros válidos para MySQL
            parametros_conexion = {
                'host': config['host'],
                'user': config['user'], 
                'password': config['password'],
                'database': config['database'],
                'port': config['port'],
                'connect_timeout': 3
            }
            conexion = mysql.connector.connect(**parametros_conexion)
            cursor = conexion.cursor()
            
            # Leer configuración de tabla
            cursor.execute("SELECT host, usuario, password, base_datos, puerto, base_url FROM datos_host_local WHERE activo = 1 LIMIT 1")
            resultado = cursor.fetchone()
            
            if resultado:
                host, user, password, database, port, base_url = resultado
                config_tabla = {
                    'host': host,
                    'user': user,
                    'password': password,
                    'database': database,
                    'port': port,
                    'base_url': base_url or "http://localhost:5000"  # ✅ NUEVO
                }
                print(f"[DEBUG] 📋 Configuración de tabla: {user}@{host} - URL: {config_tabla['base_url']}")
                
                # Probar si funciona
                try:
                    # ✅ FILTRAR parámetros válidos para MySQL
                    parametros_tabla = {k: v for k, v in config_tabla.items() 
                                      if k in ['host', 'user', 'password', 'database', 'port']}
                    conexion_tabla = mysql.connector.connect(**parametros_tabla, connect_timeout=3)
                    if conexion_tabla.is_connected():
                        print("[SUCCESS] ✅ Configuración de tabla FUNCIONA")
                        
                        # Guardar en archivo externo para próxima vez
                        guardar_configuracion_externa(config_tabla)
                        
                        conexion_tabla.close()
                        cursor.close()
                        conexion.close()
                        return config_tabla
                    conexion_tabla.close()
                except Error as e:
                    print(f"[DEBUG] ❌ Configuración de tabla no funciona: {e}")
            
            cursor.close()
            conexion.close()
        except Error:
            continue
    
    print("[DEBUG] ❌ No se pudo obtener configuración automática")
    return None

def conectar_local(parent=None):
    """
    Conexión DIRECTA a MySQL LOCAL para 'databaseapp'
    """
    print("\n" + "="*50)
    print("[DEBUG] 🚀 INICIANDO CONEXIÓN LOCAL")
    print("="*50)
    
    global CREDENCIALES_LOCALES_TEMPORALES
    
    # PRIMERO: Intentar conexión automática (archivo -> tabla)
    print("[DEBUG] 1. Intentando conexión automática...")
    config_automatica = obtener_configuracion_automatica()
    
    if config_automatica:
        print(f"[DEBUG] ✅ Configuración automática obtenida: {config_automatica['user']}@{config_automatica['host']}")
        try:
            # ✅ FILTRAR parámetros válidos para MySQL
            parametros_conexion = {k: v for k, v in config_automatica.items() 
                                 if k in ['host', 'user', 'password', 'database', 'port']}
            conexion = mysql.connector.connect(**parametros_conexion, connect_timeout=8)
            if conexion.is_connected():
                print("[SUCCESS] 🎉 Conexión automática EXITOSA")
                # Actualizar variables globales
                CREDENCIALES_LOCALES_TEMPORALES = {
                    'host': config_automatica['host'],
                    'user': config_automatica['user'],
                    'password': config_automatica['password'],
                    'port': config_automatica['port'],
                    'base_url': config_automatica.get('base_url', 'http://localhost:5000')  # ✅ NUEVO
                }
                return conexion
        except Error as e:
            print(f"[DEBUG] ❌ Conexión automática falló: {e}")
    
    # SEGUNDO: Si no funciona automático, es primera instalación o necesita reconfiguración
    print("[DEBUG] 2. Primera instalación o reconfiguración necesaria...")
    
    # Intentar configuraciones automáticas rápidas
    configuraciones_rapidas = [
        {'host': "localhost", 'user': "root", 'password': "", 'database': "databaseapp", 'port': 3306, 'base_url': "http://localhost:5000"},
        {'host': "localhost", 'user': "root", 'password': "root", 'database': "databaseapp", 'port': 3306, 'base_url': "http://localhost:5000"},
    ]
    
    for config in configuraciones_rapidas:
        try:
            print(f"[DEBUG] 🔄 Probando rápida: {config['user']}@{config['host']}")
            # ✅ FILTRAR parámetros válidos para MySQL
            parametros_conexion = {k: v for k, v in config.items() 
                                 if k in ['host', 'user', 'password', 'database', 'port']}
            conexion = mysql.connector.connect(**parametros_conexion, connect_timeout=3)
            if conexion.is_connected():
                print(f"[SUCCESS] ✅ Conexión rápida exitosa")
                
                # Preguntar si guardar esta configuración
                respuesta = QMessageBox.question(parent, "Configuración Encontrada", 
                    f"Se encontró una configuración automática:\n\n"
                    f"Host: {config['host']}\nUsuario: {config['user']}\nBase URL: {config['base_url']}\n\n"
                    f"¿Desea usar y guardar esta configuración?",
                    QMessageBox.Yes | QMessageBox.No)
                
                if respuesta == QMessageBox.Yes:
                    credenciales = {
                        'host': config['host'],
                        'user': config['user'],
                        'password': config['password'],
                        'port': config['port'],
                        'base_url': config['base_url']  # ✅ NUEVO
                    }
                    if conectar_y_guardar_configuracion(credenciales, parent):
                        conexion.close()
                        # ✅ FILTRAR parámetros válidos para MySQL
                        parametros_conexion = {k: v for k, v in config.items() 
                                             if k in ['host', 'user', 'password', 'database', 'port']}
                        return mysql.connector.connect(**parametros_conexion, connect_timeout=5)
                
                conexion.close()
                break
        except Error:
            continue
    
    # TERCERO: Pedir credenciales al usuario (PRIMERA INSTALACIÓN)
    print("[DEBUG] 3. Solicitando credenciales para primera instalación...")
    
    credenciales = obtener_credenciales_mysql(parent, False)
    
    if not credenciales:
        print("[ERROR] ❌ Usuario canceló la configuración")
        return None
    
    print(f"[DEBUG] Credenciales obtenidas: {credenciales['user']}@{credenciales['host']}")
    
    # Procesar y guardar las nuevas credenciales
    CREDENCIALES_LOCALES_TEMPORALES = credenciales.copy()
    
    if conectar_y_guardar_configuracion(credenciales, parent):
        print("[SUCCESS] ✅ Configuración guardada exitosamente")
        credenciales_con_db = credenciales.copy()
        credenciales_con_db['database'] = "databaseapp"
        # ✅ FILTRAR parámetros válidos para MySQL
        parametros_conexion = {k: v for k, v in credenciales_con_db.items() 
                             if k in ['host', 'user', 'password', 'database', 'port']}
        return mysql.connector.connect(**parametros_conexion, connect_timeout=5)
    else:
        print("[ERROR] ❌ No se pudo guardar la configuración")
    
    return None

def inicializar_base_datos_local(parent=None):
    """
    Función principal para inicializar solo la DB local
    """
    print("Inicializando base de datos LOCAL...")
    conexion = conectar_local(parent)
    
    if conexion:
        print("[SUCCESS] Base de datos local inicializada correctamente")
        conexion.close()
        return True
    else:
        print("[ERROR] No se pudo inicializar base de datos local")
        return False

def obtener_configuracion_hosting(parent=None):
    """
    Leer configuración del servidor REMOTO desde la tabla local
    """
    print("\n[DEBUG] 🌐 BUSCANDO CONFIGURACIÓN HOSTING...")
    
    conexion = conectar_local(parent)
    if not conexion:
        print("[ERROR] ❌ No se pudo conectar localmente para leer hosting")
        return None
    
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT host, usuario, password, base_datos, puerto, base_url FROM datos_hosting WHERE activo = 1 LIMIT 1")
        config = cursor.fetchone()
        cursor.close()
        
        if config:
            host, user, password, database, port, base_url = config
            print(f"[DEBUG] 📋 Configuración HOSTING encontrada: {user}@{host}:{port}/{database} - URL: {base_url}")
            
            if host and host.strip():
                print(f"[SUCCESS] ✅ Configuración HOSTING válida: {user}@{host}")
                return {
                    'host': host,
                    'user': user, 
                    'password': password,
                    'database': database,
                    'port': port,
                    'base_url': base_url or ""  # ✅ NUEVO
                }
            else:
                print("[DEBUG] ❌ Host HOSTING está vacío")
        else:
            print("[DEBUG] ❌ No hay configuración HOSTING activa")
            
        # Si no hay configuración válida, mostrar diálogo
        print("[DEBUG] Mostrando diálogo para configuración HOSTING...")
        return mostrar_dialogo_configuracion_hosting(parent)
        
    except Exception as e:
        print(f"[ERROR] ❌ Error al leer configuración HOSTING: {e}")
        return None
    finally:
        if conexion and conexion.is_connected():
            conexion.close()

def mostrar_dialogo_configuracion_hosting(parent=None):
    """
    Mostrar diálogo para configurar conexión al HOSTING REMOTO
    """
    try:
        from dialogo_config_bd import DialogoConfigBD
        
        app = QApplication.instance()
        if not app:
            app = QApplication([])
        
        QMessageBox.information(parent, "Configuración de Hosting", 
                              "Ahora necesita configurar la conexión al servidor HOSTING REMOTO.")
        
        dialogo = DialogoConfigBD(parent)
        dialogo.setWindowTitle("🌐 Configuración de Hosting Remoto")
        
        resultado = dialogo.exec_()
        print(f"[DEBUG] Resultado del diálogo hosting: {resultado}")
        
        if resultado == QDialog.Accepted:
            print("[DEBUG] Diálogo hosting aceptado, guardando configuración...")
            
            # ✅ OBTENER los datos del diálogo directamente
            host = dialogo.host_input.text().strip()
            usuario = dialogo.usuario_input.text().strip()
            password = dialogo.password_input.text()
            base_datos = dialogo.bd_input.text().strip()
            puerto = dialogo.puerto_input.value()
            base_url = dialogo.base_url_input.text().strip() if hasattr(dialogo, 'base_url_input') else ""  # ✅ NUEVO
            
            print(f"[DEBUG] Datos hosting a guardar: {usuario}@{host}:{puerto}/{base_datos} - URL: {base_url}")
            
            # ✅ GUARDAR directamente la configuración
            if guardar_configuracion_hosting(host, usuario, password, base_datos, puerto, base_url, parent):
                print("[SUCCESS] ✅ Configuración HOSTING guardada correctamente")
                # ✅ LEER la configuración recién guardada
                config_guardada = obtener_configuracion_hosting_sin_dialogo(parent)
                if config_guardada:
                    print(f"[SUCCESS] ✅ Configuración HOSTING verificada: {config_guardada['user']}@{config_guardada['host']}")
                    return config_guardada
                else:
                    print("[ERROR] ❌ No se pudo verificar la configuración HOSTING guardada")
                    return None
            else:
                print("[ERROR] ❌ No se pudo guardar la configuración HOSTING")
                return None
        else:
            QMessageBox.warning(parent, "Configuración Requerida", 
                              "Debe configurar la conexión al HOSTING para continuar.")
            return None
            
    except Exception as e:
        print(f"[ERROR] ❌ Error en diálogo HOSTING: {e}")
        return None

def obtener_configuracion_hosting_sin_dialogo(parent=None):
    """
    Leer configuración HOSTING sin mostrar diálogo
    """
    conexion = conectar_local(parent)
    if not conexion:
        return None
    
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT host, usuario, password, base_datos, puerto, base_url FROM datos_hosting WHERE activo = 1 LIMIT 1")
        config = cursor.fetchone()
        cursor.close()
        
        if config and all(config) and config[0]:
            host, user, password, database, port, base_url = config
            return {
                'host': host,
                'user': user, 
                'password': password,
                'database': database,
                'port': port,
                'base_url': base_url or ""  # ✅ NUEVO
            }
        return None
        
    except Exception as e:
        print(f"Error al leer configuración HOSTING: {e}")
        return None
    finally:
        if conexion.is_connected():
            conexion.close()

def guardar_configuracion_hosting(host, usuario, password, base_datos, puerto=3306, base_url="", parent=None):
    """
    Guardar configuración del servidor REMOTO en la tabla local
    """
    print(f"[DEBUG] 🛠️ Guardando configuración HOSTING: {usuario}@{host}:{puerto}/{base_datos} - URL: {base_url}")
    
    conexion = conectar_local(parent)
    if not conexion:
        print("[ERROR] ❌ No se pudo conectar localmente para guardar hosting")
        return False
    
    try:
        cursor = conexion.cursor()
        
        # Limpiar configuraciones anteriores
        print("[DEBUG] Limpiando configuraciones HOSTING anteriores...")
        cursor.execute("UPDATE datos_hosting SET activo = 0")
        
        # Insertar nueva configuración activa
        print("[DEBUG] Insertando nueva configuración HOSTING...")
        cursor.execute("""
            INSERT INTO datos_hosting (host, usuario, password, base_datos, puerto, base_url, activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (host, usuario, password, base_datos, puerto, base_url, True))
        
        conexion.commit()
        
        # VERIFICAR que se guardó correctamente
        cursor.execute("SELECT host, usuario, base_datos, base_url FROM datos_hosting WHERE activo = 1 LIMIT 1")
        verificacion = cursor.fetchone()
        
        cursor.close()
        conexion.close()
        
        if verificacion:
            host_verif, usuario_verif, bd_verif, url_verif = verificacion
            print(f"[SUCCESS] ✅ Configuración HOSTING guardada y verificada: {usuario_verif}@{host_verif}/{bd_verif} - URL: {url_verif}")
            return True
        else:
            print("[ERROR] ❌ No se pudo verificar el guardado HOSTING")
            return False
        
    except Exception as e:
        print(f"[ERROR] ❌ Error al guardar configuración HOSTING: {e}")
        try:
            if conexion.is_connected():
                conexion.close()
        except:
            pass
        return False

def cerrar_conexion(conexion):
    """
    Cerrar conexión de forma segura
    """
    if conexion and conexion.is_connected():
        conexion.close()

def conectar_base_datos(parent=None):
    """
    Función alias para mantener compatibilidad con código existente
    """
    return conectar_local(parent)