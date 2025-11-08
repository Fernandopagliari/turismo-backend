# -*- coding: utf-8 -*-
# database_local.py - EXCLUSIVO para base de datos LOCAL
import mysql.connector
from mysql.connector import Error
from PyQt5.QtWidgets import QMessageBox, QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt
import sys
import json
import os
import time

# -------------------------
# CACHE DE CONEXIONES PARA MEJORAR VELOCIDAD
# -------------------------
_CONEXION_CACHE = {}
_CACHE_TIMEOUT = 30  # 30 segundos para cache de conexiones
_ULTIMA_CONEXION_EXITOSA = None

def limpiar_cache_conexiones():
    """Limpia conexiones de cache antiguas"""
    global _CONEXION_CACHE
    current_time = time.time()
    keys_to_remove = []
    
    for key, (timestamp, conexion) in _CONEXION_CACHE.items():
        if current_time - timestamp > _CACHE_TIMEOUT:
            keys_to_remove.append(key)
            try:
                if conexion and conexion.is_connected():
                    conexion.close()
            except:
                pass
    
    for key in keys_to_remove:
        del _CONEXION_CACHE[key]

def obtener_clave_conexion(config):
    """Genera clave única para el cache de conexiones"""
    return f"{config.get('host','')}:{config.get('port','')}:{config.get('database','')}"

# -------------------------
# CONEXIÓN CON RECONEXIÓN AUTOMÁTICA
# -------------------------
def conectar_con_reintentos(config, max_reintentos=2, timeout=5):
    """
    Intenta conectar con reintentos automáticos - OPTIMIZADA
    """
    clave = obtener_clave_conexion(config)
    
    # Verificar cache primero
    if clave in _CONEXION_CACHE:
        timestamp, conexion_cache = _CONEXION_CACHE[clave]
        if time.time() - timestamp < _CACHE_TIMEOUT:
            try:
                if conexion_cache and conexion_cache.is_connected():
                    # Verificar que la conexión sigue activa
                    cursor = conexion_cache.cursor()
                    cursor.execute("SELECT 1")
                    cursor.close()
                    return conexion_cache
            except:
                # Conexión en cache no funciona, eliminar
                del _CONEXION_CACHE[clave]
    
    limpiar_cache_conexiones()
    
    for intento in range(max_reintentos + 1):
        try:
            # ✅ CONEXIÓN COMPATIBLE con timeout optimizado
            conexion = mysql.connector.connect(
                host=config.get('host'),
                user=config.get('user'),
                password=config.get('password'),
                database=config.get('database'),
                port=config.get('port'),
                connect_timeout=timeout,
                connection_timeout=timeout
            )
            
            if conexion.is_connected():
                global _ULTIMA_CONEXION_EXITOSA
                _ULTIMA_CONEXION_EXITOSA = time.time()
                
                # Guardar en cache
                _CONEXION_CACHE[clave] = (time.time(), conexion)
                return conexion
                
        except Error as e:
            if intento == max_reintentos:
                raise e
            # Esperar antes del reintento (con backoff exponencial)
            time.sleep(1 * (intento + 1))
    
    return None

# ✅ SOLUCIÓN DEFINITIVA PARA WINDOWS UPDATE
_original_connect = mysql.connector.connect

def conectar_compatible(**kwargs):
    """
    Conexión compatible con cualquier configuración de Windows Update - OPTIMIZADA
    """
    # Intentar con charset=utf8 primero (el más compatible)
    try:
        kwargs_compatible = kwargs.copy()
        kwargs_compatible['charset'] = 'utf8'
        kwargs_compatible['use_unicode'] = True
        kwargs_compatible['connect_timeout'] = kwargs.get('connect_timeout', 5)
        return _original_connect(**kwargs_compatible)
    except Error as e:
        if "utf8" in str(e).lower():
            # Si falla con utf8, intentar SIN charset
            try:
                kwargs_clean = kwargs.copy()
                kwargs_clean.pop('charset', None)
                kwargs_clean.pop('use_unicode', None)
                return _original_connect(**kwargs_clean)
            except Error as e2:
                # Si todo falla, intentar con latin1 (más compatible)
                try:
                    kwargs_latin = kwargs.copy()
                    kwargs_latin['charset'] = 'latin1'
                    return _original_connect(**kwargs_latin)
                except:
                    raise e2
        else:
            raise e

# Aplicar el método compatible
mysql.connector.connect = conectar_compatible

# ✅ FUNCIÓN PARA DETECCIÓN AUTOMÁTICA DE PUERTO
def obtener_puerto_automatico():
    """
    Determina automáticamente qué puerto usar - OPTIMIZADA
    """
    puertos = [3306, 3307, 3308]
    
    for puerto in puertos:
        try:
            conexion = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                port=puerto,
                connect_timeout=2  # Timeout más corto para detección
            )
            conexion.close()
            return puerto
        except:
            continue
    
    return 3307  # Puerto por defecto

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
            
        self.setFixedSize(450, 420)
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
        # Usar puerto automático como valor por defecto
        puerto_auto = obtener_puerto_automatico()
        self.puerto_input.setText(str(puerto_auto))
        self.puerto_input.setPlaceholderText(str(puerto_auto))
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
            # ✅ USAR la conexión compatible
            conexion = mysql.connector.connect(
                host=host,
                user=usuario,
                password=password,
                port=int(puerto),
                connect_timeout=8
            )
            
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
                'base_url': self.base_url_input.text().strip()
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
            'base_url': credenciales.get('base_url', 'http://localhost:5000'),
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        return False

def cargar_configuracion_externa():
    """Cargar configuración desde archivo externo"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            return config
        return None
    except Exception as e:
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
    except Exception as e:
        pass
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
        
    except Exception as e:
        pass
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
        
    except Exception as e:
        pass
    finally:
        cursor.close()

def conectar_y_guardar_configuracion(credenciales, parent=None):
    """
    Conectar con credenciales y guardarlas en tabla Y archivo externo
    """
    global CREDENCIALES_LOCALES_TEMPORALES
    
    try:
        # ✅ GUARDAR como temporales inmediatamente
        CREDENCIALES_LOCALES_TEMPORALES = credenciales.copy()
        
        # Primero conectar sin base de datos para crearla
        conexion = mysql.connector.connect(
            host=credenciales['host'],
            user=credenciales['user'],
            password=credenciales['password'],
            port=credenciales['port'],
            connect_timeout=5
        )
        
        cursor = conexion.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS databaseapp")
        
        # Ahora conectar a la base de datos específica
        conexion_db = mysql.connector.connect(
            host=credenciales['host'],
            user=credenciales['user'],
            password=credenciales['password'],
            database="databaseapp",
            port=credenciales['port'],
            connect_timeout=5
        )
        
        # Crear tablas si no existen
        crear_tabla_licencia(conexion_db)
        crear_tabla_datos_host_local(conexion_db)
        crear_tabla_datos_hosting(conexion_db)
        
        # ✅ GUARDAR en tabla datos_host_local
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
            credenciales.get('base_url', 'http://localhost:5000'),
            True
        ))
        
        conexion_db.commit()
        
        # ✅ GUARDAR en archivo externo
        guardar_configuracion_externa(credenciales)
        
        # VERIFICAR que se guardó correctamente
        cursor_db.execute("SELECT host, usuario, base_url FROM datos_host_local WHERE activo = 1")
        verificacion = cursor_db.fetchone()
        
        cursor.close()
        conexion.close()
        cursor_db.close()
        conexion_db.close()
        
        return True
        
    except Error as e:
        return False

def obtener_configuracion_automatica():
    """
    Obtener configuración automáticamente (archivo externo -> tabla)
    """
    # 1. PRIMERO: Buscar en archivo externo
    config_externa = cargar_configuracion_externa()
    
    if config_externa:
        try:
            conexion = conectar_con_reintentos(config_externa, max_reintentos=1, timeout=3)
            if conexion and conexion.is_connected():
                conexion.close()
                return config_externa
        except Error as e:
            pass
    
    # 2. SEGUNDO: Intentar leer de la tabla con métodos alternativos
    # ✅ USAR PUERTO AUTOMÁTICO EN CONFIGURACIONES DE PRUEBA
    puerto_auto = obtener_puerto_automatico()
    configuraciones_prueba = [
        {'host': "localhost", 'user': "root", 'password': "", 'database': "databaseapp", 'port': puerto_auto, 'base_url': "http://localhost:5000"},
        {'host': "localhost", 'user': "root", 'password': "root", 'database': "databaseapp", 'port': puerto_auto, 'base_url': "http://localhost:5000"},
        {'host': "127.0.0.1", 'user': "root", 'password': "", 'database': "databaseapp", 'port': puerto_auto, 'base_url': "http://localhost:5000"},
    ]
    
    for config in configuraciones_prueba:
        try:
            conexion = conectar_con_reintentos(config, max_reintentos=1, timeout=2)
            if conexion and conexion.is_connected():
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
                        'base_url': base_url or "http://localhost:5000"
                    }
                    
                    # Probar si funciona
                    try:
                        conexion_tabla = conectar_con_reintentos(config_tabla, max_reintentos=1, timeout=2)
                        if conexion_tabla and conexion_tabla.is_connected():
                            # Guardar en archivo externo para próxima vez
                            guardar_configuracion_externa(config_tabla)
                            
                            conexion_tabla.close()
                            cursor.close()
                            conexion.close()
                            return config_tabla
                        if conexion_tabla:
                            conexion_tabla.close()
                    except Error as e:
                        pass
                
                cursor.close()
                conexion.close()
        except Error:
            continue
    
    return None

def conectar_local(parent=None):
    """
    Conexión DIRECTA a MySQL LOCAL para 'databaseapp' - MODO COMPATIBILIDAD
    """
    global CREDENCIALES_LOCALES_TEMPORALES
    
    # PRIMERO: Intentar conexión automática
    config_automatica = obtener_configuracion_automatica()
    
    if config_automatica:
        try:
            conexion = conectar_con_reintentos(config_automatica, max_reintentos=1, timeout=5)
            if conexion and conexion.is_connected():
                # Actualizar variables globales
                CREDENCIALES_LOCALES_TEMPORALES = {
                    'host': config_automatica['host'],
                    'user': config_automatica['user'],
                    'password': config_automatica['password'],
                    'port': config_automatica['port'],
                    'base_url': config_automatica.get('base_url', 'http://localhost:5000')
                }
                return conexion
        except Error as e:
            pass
    
    # SEGUNDO: Intentar configuraciones automáticas rápidas
    puerto_auto = obtener_puerto_automatico()
    configuraciones_rapidas = [
        {'host': "localhost", 'user': "root", 'password': "", 'database': "databaseapp", 'port': puerto_auto, 'base_url': "http://localhost:5000"},
        {'host': "localhost", 'user': "root", 'password': "root", 'database': "databaseapp", 'port': puerto_auto, 'base_url': "http://localhost:5000"},
    ]
    
    for config in configuraciones_rapidas:
        try:
            conexion = conectar_con_reintentos(config, max_reintentos=1, timeout=2)
            if conexion and conexion.is_connected():
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
                        'base_url': config['base_url']
                    }
                    if conectar_y_guardar_configuracion(credenciales, parent):
                        conexion.close()
                        return conectar_con_reintentos(config, max_reintentos=1, timeout=5)
                
                conexion.close()
                break
        except Error:
            continue
    
    # TERCERO: Pedir credenciales al usuario (PRIMERA INSTALACIÓN)
    credenciales = obtener_credenciales_mysql(parent, False)
    
    if not credenciales:
        return None
    
    # Procesar y guardar las nuevas credenciales
    CREDENCIALES_LOCALES_TEMPORALES = credenciales.copy()
    
    if conectar_y_guardar_configuracion(credenciales, parent):
        return conectar_con_reintentos({
            'host': credenciales['host'],
            'user': credenciales['user'],
            'password': credenciales['password'],
            'database': "databaseapp",
            'port': credenciales['port']
        }, max_reintentos=1, timeout=5)
    
    return None

def inicializar_base_datos_local(parent=None):
    """
    Función principal para inicializar solo la DB local
    """
    conexion = conectar_local(parent)
    
    if conexion:
        conexion.close()
        return True
    else:
        return False

def obtener_configuracion_hosting(parent=None):
    """
    Leer configuración del servidor REMOTO desde la tabla local
    """
    conexion = conectar_local(parent)
    if not conexion:
        return None
    
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT host, usuario, password, base_datos, puerto, base_url FROM datos_hosting WHERE activo = 1 LIMIT 1")
        config = cursor.fetchone()
        cursor.close()
        
        if config:
            host, user, password, database, port, base_url = config
            
            if host and host.strip():
                return {
                    'host': host,
                    'user': user, 
                    'password': password,
                    'database': database,
                    'port': port,
                    'base_url': base_url or ""
                }
            
        # Si no hay configuración válida, mostrar diálogo
        return mostrar_dialogo_configuracion_hosting(parent)
        
    except Exception as e:
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
        
        if resultado == QDialog.Accepted:
            # ✅ OBTENER los datos del diálogo directamente
            host = dialogo.host_input.text().strip()
            usuario = dialogo.usuario_input.text().strip()
            password = dialogo.password_input.text()
            base_datos = dialogo.bd_input.text().strip()
            puerto = dialogo.puerto_input.value()
            base_url = dialogo.base_url_input.text().strip() if hasattr(dialogo, 'base_url_input') else ""
            
            # ✅ GUARDAR directamente la configuración
            if guardar_configuracion_hosting(host, usuario, password, base_datos, puerto, base_url, parent):
                # ✅ LEER la configuración recién guardada
                config_guardada = obtener_configuracion_hosting_sin_dialogo(parent)
                if config_guardada:
                    return config_guardada
                else:
                    return None
            else:
                return None
        else:
            QMessageBox.warning(parent, "Configuración Requerida", 
                              "Debe configurar la conexión al HOSTING para continuar.")
            return None
            
    except Exception as e:
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
                'base_url': base_url or ""
            }
        return None
        
    except Exception as e:
        return None
    finally:
        if conexion.is_connected():
            conexion.close()

def guardar_configuracion_hosting(host, usuario, password, base_datos, puerto=3306, base_url="", parent=None):
    """
    Guardar configuración del servidor REMOTO en la tabla local
    """
    conexion = conectar_local(parent)
    if not conexion:
        return False
    
    try:
        cursor = conexion.cursor()
        
        # Limpiar configuraciones anteriores
        cursor.execute("UPDATE datos_hosting SET activo = 0")
        
        # Insertar nueva configuración activa
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
            return True
        else:
            return False
        
    except Exception as e:
        try:
            if conexion.is_connected():
                conexion.close()
        except:
            pass
        return False

def cerrar_conexion(conexion):
    """
    Cerrar conexión de forma segura - ACTUALIZADA
    """
    if conexion and conexion.is_connected():
        conexion.close()
    
    # Limpiar cache periódicamente
    if len(_CONEXION_CACHE) > 5:  # Máximo 5 conexiones en cache
        limpiar_cache_conexiones()

def conectar_base_datos(parent=None):
    """
    Función alias para mantener compatibilidad con código existente
    """
    return conectar_local(parent)