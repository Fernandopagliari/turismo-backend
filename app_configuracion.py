# -*- coding: utf-8 -*-
import base64
import os
import requests
from PyQt5 import uic
from database_hosting import conectar_hosting as conectar_base_datos
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QApplication, QWidget, QMessageBox, QLabel
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush, QPen, QColor, QPainterPath
from PyQt5.QtCore import Qt
import time
import hashlib
from utils.image_utils import procesar_imagen


# -------------------------
# CACHE DE IMÁGENES MEJORADO
# -------------------------
_image_cache = {}
_CACHE_MAX_SIZE = 100
_CACHE_TIMEOUT = 10  # ✅ REDUCIDO a 10 segundos para mejor performance

def limpiar_cache_antiguo():
    """Limpia entradas de cache antiguas"""
    global _image_cache
    current_time = time.time()
    keys_to_remove = []
    
    for key, (timestamp, pixmap) in _image_cache.items():
        if current_time - timestamp > _CACHE_TIMEOUT:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del _image_cache[key]

def obtener_clave_cache(ruta_imagen, size=None):
    """Genera clave única para el cache"""
    clave = f"{ruta_imagen}_{size}"
    return hashlib.md5(clave.encode()).hexdigest()

def imagen_a_base64(ruta_imagen):
    """Convierte imagen a Base64 para guardar en BD"""
    try:
        with open(ruta_imagen, "rb") as file:
            image_data = file.read()
            base64_encoded = base64.b64encode(image_data).decode('utf-8')
            return f"data:image/jpeg;base64,{base64_encoded}"
    except Exception as e:
        print(f"❌ Error convirtiendo imagen a base64: {e}")
        return None

def convertir_ruta_produccion(ruta_absoluta):
    """Convierte rutas absolutas a rutas relativas - VERSIÓN MEJORADA"""
    if not ruta_absoluta:
        return ""
    
    # ✅ Si ya es una URL, retornar vacío (no necesita conversión)
    if _is_url(ruta_absoluta):
        return ""
    
    if not os.path.exists(ruta_absoluta):
        print(f"⚠️ Ruta no existe: {ruta_absoluta}")
        return ""
    
    ruta_normalizada = os.path.normpath(ruta_absoluta)
    
    # Buscar "assets/imagenes"
    target = "assets" + os.sep + "imagenes" + os.sep
    idx = ruta_normalizada.lower().find(target.lower())
    
    if idx != -1:
        ruta_relativa = ruta_normalizada[idx + len(target):]
        resultado = f"assets/imagenes/{ruta_relativa}".replace("\\", "/")
        print(f"✅ Ruta convertida: {ruta_absoluta} -> {resultado}")
        return resultado
    
    nombre_archivo = os.path.basename(ruta_absoluta)
    resultado = f"assets/imagenes/{nombre_archivo}"
    print(f"📁 Usando nombre archivo: {resultado}")
    return resultado

# -------------------------
# SISTEMA DE URLs REMOTAS MEJORADO
# -------------------------
def _is_url(path):
    """Verifica si una ruta es una URL"""
    return isinstance(path, str) and (path.startswith("http://") or path.startswith("https://"))

def es_video(ruta):
    if not ruta:
        return False
    ruta = ruta.lower()
    return ruta.endswith(".webm") or ruta.endswith(".mp4")

def obtener_url_base_hosting():
    """Obtiene la URL base desde la base de datos - NUEVA FUNCIÓN"""
    try:
        conn = conectar_base_datos()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT base_url FROM datos_hosting WHERE activo = 1 LIMIT 1")
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if resultado and resultado.get('base_url'):
            base_url = resultado['base_url'].strip()
            if base_url:
                if not base_url.endswith('/'):
                    base_url += '/'
                print(f"🌐 URL base obtenida: {base_url}")
                return base_url
    except Exception as e:
        print(f"❌ Error obteniendo URL base: {e}")
    return ""

def obtener_url_remota(ruta_relativa: str) -> str:
    """Construye URL remota basada en la configuración de hosting - MEJORADA"""
    if not ruta_relativa:
        return ""
    
    # ✅ Si ya es una URL completa, retornarla directamente
    if _is_url(ruta_relativa):
        return ruta_relativa
    
    base_url = obtener_url_base_hosting()
    if not base_url:
        print("❌ No se pudo obtener URL base")
        return ""
    
    # Limpiar y construir URL
    ruta_limpia = ruta_relativa.lstrip('/')
    url_completa = f"{base_url}{ruta_limpia}"
    print(f"🔗 URL remota construida: {url_completa}")
    return url_completa

def verificar_url_remota(url: str) -> bool:
    """Verifica si una URL remota es accesible - MEJORADA"""
    if not url:
        return False
    
    try:
        print(f"🔍 Verificando URL: {url}")
        response = requests.head(url, timeout=5, allow_redirects=True)
        accesible = response.status_code == 200
        print(f"✅ URL accesible: {accesible} (Status: {response.status_code})")
        return accesible
    except Exception as e:
        print(f"❌ URL no accesible: {e}")
        return False

def resolver_ruta_hibrida(ruta_absoluta_db: str, ruta_relativa_db: str) -> str:
    """
    ✅ MEJORADO: Busca imágenes en REMOTO → LOCAL con logs detallados
    """
    # Limpiar cache antiguo periódicamente
    if len(_image_cache) > _CACHE_MAX_SIZE:
        limpiar_cache_antiguo()
    
    print(f"🔄 Resolviendo ruta híbrida:")
    print(f"   - Ruta absoluta: {ruta_absoluta_db}")
    print(f"   - Ruta relativa: {ruta_relativa_db}")

    # 1. PRIMERO: Buscar en REMOTO usando ruta relativa
    if ruta_relativa_db and ruta_relativa_db.strip():
        url_remota = obtener_url_remota(ruta_relativa_db.strip())
        if url_remota and verificar_url_remota(url_remota):
            print(f"🎯 Usando URL remota: {url_remota}")
            return url_remota
        else:
            print("⚠️  URL remota no disponible")

    # 2. SEGUNDO: Buscar en LOCAL con ruta absoluta
    if ruta_absoluta_db and os.path.exists(ruta_absoluta_db):
        print(f"📁 Usando ruta local absoluta: {ruta_absoluta_db}")
        return ruta_absoluta_db
    
    # 3. TERCERO: Buscar en estructura del proyecto con ruta relativa
    if ruta_relativa_db and ruta_relativa_db.strip():
        # Limpiar ruta relativa
        ruta_rel_limpia = ruta_relativa_db.strip().lstrip('/')
        
        rutas_posibles = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                        "turismo-frontend", "public", ruta_rel_limpia),
            os.path.join(os.getcwd(), "turismo-frontend", "public", ruta_rel_limpia),
            os.path.join(os.path.dirname(__file__), "..", "..", "turismo-frontend", "public", ruta_rel_limpia),
        ]
        
        for ruta in rutas_posibles:
            ruta_abs = os.path.abspath(ruta)
            if os.path.exists(ruta_abs):
                print(f"📂 Encontrado en estructura proyecto: {ruta_abs}")
                return ruta_abs
            else:
                print(f"🔍 No encontrado: {ruta_abs}")

    print("❌ No se pudo resolver ninguna ruta para la imagen")
    return ""

def cargar_imagen_desde_ruta(ruta_imagen: str, size: tuple = None):
    """
    ✅ MEJORADO: Carga imagen desde URL remota o archivo local con cache
    """
    if not ruta_imagen:
        print("❌ Ruta de imagen vacía")
        return None

    # Verificar cache primero
    cache_key = obtener_clave_cache(ruta_imagen, size)
    if cache_key in _image_cache:
        timestamp, pixmap = _image_cache[cache_key]
        if time.time() - timestamp < _CACHE_TIMEOUT:
            print(f"⚡ Imagen cargada desde cache: {ruta_imagen}")
            return pixmap
        else:
            del _image_cache[cache_key]

    try:
        print(f"🔄 Cargando imagen: {ruta_imagen}")
        
        # ✅ MANEJAR URL REMOTA
        if _is_url(ruta_imagen):
            print(f"🌐 Descargando imagen remota: {ruta_imagen}")
            response = requests.get(ruta_imagen, timeout=10)  # ✅ Timeout aumentado
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                if not pixmap.isNull():
                    if size:
                        pixmap = pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    # Guardar en cache
                    _image_cache[cache_key] = (time.time(), pixmap)
                    print(f"✅ Imagen remota cargada exitosamente")
                    return pixmap
                else:
                    print("❌ Error: Pixmap nulo desde datos de respuesta")
            else:
                print(f"❌ Error HTTP: {response.status_code}")
            return None
        
        # ✅ MANEJAR ARCHIVO LOCAL
        elif os.path.exists(ruta_imagen):
            print(f"📁 Cargando imagen local: {ruta_imagen}")
            pixmap = QPixmap(ruta_imagen)
            if not pixmap.isNull():
                if size:
                    pixmap = pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
                # Guardar en cache
                _image_cache[cache_key] = (time.time(), pixmap)
                print(f"✅ Imagen local cargada exitosamente")
                return pixmap
            else:
                print("❌ Error: No se pudo cargar pixmap desde archivo")
        
        print(f"❌ No se pudo cargar imagen: {ruta_imagen}")
        return None
        
    except Exception as e:
        print(f"💥 Excepción cargando imagen: {e}")
        return None

class VentanaConfiguracion(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlag(Qt.Window)
        self.resize(700, 500)
        self.parent_widget = parent

        # Ruta absoluta al archivo .ui
        ruta_ui = os.path.join(
            os.path.dirname(__file__),
            "interfaz",
            "configuracion_app.ui"
        )
        if not os.path.exists(ruta_ui):
            raise FileNotFoundError(f"No se encontró el archivo UI en: {ruta_ui}")

        uic.loadUi(ruta_ui, self)

        self.centrar_ventana()

        self.setWindowTitle("Configuración de la App")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMinMaxButtonsHint)

        # Inicializar variables
        self.config_seleccionada_id = None
        self.config_inactiva_id = None

        # Cargar configuraciones
        self.cargar_configuracion_activa()
        self.cargar_configuracion_inactiva()

        # Conectar botones
        self.btnAgregarConfig.clicked.connect(self.agregar_configuracion)
        self.btnModificarConfig.clicked.connect(self.modificar_configuracion)
        self.btnDesactivarConfig.clicked.connect(self.desactivar_configuracion)
        self.btnReactivarConfiguracion.clicked.connect(self.reactivar_configuracion)
        self.btnLimpiarFormulario.clicked.connect(self.limpiar_formulario)
        self.btnLogo.clicked.connect(self.seleccionar_logo)
        self.btnIconoAbrir.clicked.connect(self.seleccionar_icono_abrir)
        self.btnIconoCerrar.clicked.connect(self.seleccionar_icono_cerrar)
        self.btnHeroImagen.clicked.connect(self.seleccionar_hero_imagen)
        self.btnCerrar.clicked.connect(self.close)

        self.Tabla_configuracion_activa.cellClicked.connect(self.seleccionar_config_activa)
        self.Tabla_configuraciones_inactiva.cellClicked.connect(self.seleccionar_config_inactiva)

    def centrar_ventana(self):
        pantalla = QApplication.primaryScreen().availableGeometry()
        ventana = self.frameGeometry()
        ventana.moveCenter(pantalla.center())
        self.move(ventana.topLeft())

    def closeEvent(self, event):
        if self.parent():
            self.parent().mostrar_menu_lateral()
        super().closeEvent(event)

    # ------------------ CRUD MEJORADO -------------------

    def cargar_configuracion_activa(self):
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT id_config, titulo_app, 
                    logo_app, logo_app_ruta_relativa,
                    icono_hamburguesa, icono_hamburguesa_ruta_relativa,
                    icono_cerrar, icono_cerrar_ruta_relativa,
                    hero_titulo, hero_imagen, hero_imagen_ruta_relativa,
                    footer_texto, direccion_facebook, direccion_instagram, 
                    direccion_twitter, direccion_youtube, correo_electronico
                FROM configuracion_app WHERE habilitar = 1
            """)
            resultados = cursor.fetchall()
            conexion.close()

            columnas = ["ID", "Título", "Logo", "Logo Ruta Rel", "Icono Abrir", "Icono Abrir Ruta Rel", 
                        "Icono Cerrar", "Icono Cerrar Ruta Rel", "Hero Título", "Hero Imagen", "Hero Imagen Ruta Rel",
                        "Footer", "Facebook", "Instagram", "Twitter", "Youtube", "Correo"]
            
            self.Tabla_configuracion_activa.setColumnCount(len(columnas))
            self.Tabla_configuracion_activa.setHorizontalHeaderLabels(columnas)
            self.Tabla_configuracion_activa.setRowCount(0)

            for row_number, row_data in enumerate(resultados):
                self.Tabla_configuracion_activa.insertRow(row_number)
                for column_number, data in enumerate(row_data):
                    item = QTableWidgetItem(str(data) if data is not None else "")
                    self.Tabla_configuracion_activa.setItem(row_number, column_number, item)

            print(f"✅ Configuraciones activas cargadas: {len(resultados)} registros")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudieron cargar las configuraciones activas: {e}")
            print(f"❌ Error cargando configuraciones activas: {e}")

    def cargar_configuracion_inactiva(self):
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT id_config, titulo_app, 
                    logo_app, logo_app_ruta_relativa,
                    icono_hamburguesa, icono_hamburguesa_ruta_relativa,
                    icono_cerrar, icono_cerrar_ruta_relativa,
                    hero_titulo, hero_imagen, hero_imagen_ruta_relativa,
                    footer_texto, direccion_facebook, direccion_instagram, 
                    direccion_twitter, direccion_youtube, correo_electronico
                FROM configuracion_app WHERE habilitar = 0
            """)
            resultados = cursor.fetchall()
            conexion.close()

            columnas = ["ID", "Título", "Logo", "Logo Ruta Rel", "Icono Abrir", "Icono Abrir Ruta Rel", 
                        "Icono Cerrar", "Icono Cerrar Ruta Rel", "Hero Título", "Hero Imagen", "Hero Imagen Ruta Rel",
                        "Footer", "Facebook", "Instagram", "Twitter", "Youtube", "Correo"]
            
            self.Tabla_configuraciones_inactiva.setColumnCount(len(columnas))
            self.Tabla_configuraciones_inactiva.setHorizontalHeaderLabels(columnas)
            self.Tabla_configuraciones_inactiva.setRowCount(0)

            for row_number, row_data in enumerate(resultados):
                self.Tabla_configuraciones_inactiva.insertRow(row_number)
                for column_number, data in enumerate(row_data):
                    item = QTableWidgetItem(str(data) if data is not None else "")
                    self.Tabla_configuraciones_inactiva.setItem(row_number, column_number, item)
                    
            print(f"✅ Configuraciones inactivas cargadas: {len(resultados)} registros")
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudieron cargar las configuraciones inactivas: {e}")
            print(f"❌ Error cargando configuraciones inactivas: {e}")
                
    def seleccionar_config_activa(self, fila, columna):
        print(f"🎯 Seleccionando configuración activa - Fila: {fila}, Columna: {columna}")
        
        def obtener_texto(f, c):
            item = self.Tabla_configuracion_activa.item(f, c)
            return item.text() if item else ""

        self.config_seleccionada_id = obtener_texto(fila, 0)
        self.lineEdit_titulo_app.setText(obtener_texto(fila, 1))
        
        # ✅ MEJORADO: Usar búsqueda híbrida mejorada
        ruta_absoluta_logo = obtener_texto(fila, 2)
        ruta_relativa_logo = obtener_texto(fila, 3)
        ruta_final_logo = resolver_ruta_hibrida(ruta_absoluta_logo, ruta_relativa_logo)
        self.lineEdit_logo_app.setText(ruta_final_logo)
        
        ruta_absoluta_icono_abrir = obtener_texto(fila, 4)
        ruta_relativa_icono_abrir = obtener_texto(fila, 5)
        ruta_final_icono_abrir = resolver_ruta_hibrida(ruta_absoluta_icono_abrir, ruta_relativa_icono_abrir)
        self.lineEdit_icono_abrir.setText(ruta_final_icono_abrir)
        
        ruta_absoluta_icono_cerrar = obtener_texto(fila, 6)
        ruta_relativa_icono_cerrar = obtener_texto(fila, 7)
        ruta_final_icono_cerrar = resolver_ruta_hibrida(ruta_absoluta_icono_cerrar, ruta_relativa_icono_cerrar)
        self.lineEdit_icono_cerrar.setText(ruta_final_icono_cerrar)
        
        self.lineEdit_hero_titulo.setText(obtener_texto(fila, 8))
        
        ruta_absoluta_hero = obtener_texto(fila, 9)
        ruta_relativa_hero = obtener_texto(fila, 10)
        ruta_final_hero = resolver_ruta_hibrida(ruta_absoluta_hero, ruta_relativa_hero)
        self.lineEdit_hero_imagen.setText(ruta_final_hero)

        self.lineEdit_footer_texto.setText(obtener_texto(fila, 11))
        self.lineEdit_direccion_facebook.setText(obtener_texto(fila, 12))
        self.lineEdit_direccion_instagram.setText(obtener_texto(fila, 13))
        self.lineEdit_direccion_twitter.setText(obtener_texto(fila, 14))
        self.lineEdit_direccion_youtube.setText(obtener_texto(fila, 15))
        self.lineEdit_direccion_correo.setText(obtener_texto(fila, 16))

        # ✅ MEJORADO: Mostrar imágenes con logs detallados
        print("🖼️  Cargando imágenes para configuración activa...")
        self.mostrar_imagen_config(ruta_final_logo, self.label_logo_app, 50)
        self.mostrar_imagen_config(ruta_final_icono_abrir, self.label_icono_abrir, 50)
        self.mostrar_imagen_config(ruta_final_icono_cerrar, self.label_icono_cerrar, 50)
        self.mostrar_imagen_config(ruta_final_hero, self.label_imagen_central, 100)

        # Botones
        self.btnAgregarConfig.setEnabled(False)
        self.btnModificarConfig.setEnabled(True)
        self.btnDesactivarConfig.setEnabled(True)
        self.btnReactivarConfiguracion.setEnabled(False)

        print(f"✅ Configuración activa {self.config_seleccionada_id} cargada exitosamente")

    def seleccionar_config_inactiva(self, fila, columna):
        print(f"🎯 Seleccionando configuración inactiva - Fila: {fila}, Columna: {columna}")
        
        def obtener_texto(f, c):
            item = self.Tabla_configuraciones_inactiva.item(f, c)
            return item.text() if item else ""

        self.config_inactiva_id = obtener_texto(fila, 0)
        self.lineEdit_titulo_app.setText(obtener_texto(fila, 1))
        
        # ✅ MEJORADO: Usar búsqueda híbrida también para inactivas
        ruta_absoluta_logo = obtener_texto(fila, 2)
        ruta_relativa_logo = obtener_texto(fila, 3)
        ruta_final_logo = resolver_ruta_hibrida(ruta_absoluta_logo, ruta_relativa_logo)
        self.lineEdit_logo_app.setText(ruta_final_logo)
        
        ruta_absoluta_icono_abrir = obtener_texto(fila, 4)
        ruta_relativa_icono_abrir = obtener_texto(fila, 5)
        ruta_final_icono_abrir = resolver_ruta_hibrida(ruta_absoluta_icono_abrir, ruta_relativa_icono_abrir)
        self.lineEdit_icono_abrir.setText(ruta_final_icono_abrir)
        
        ruta_absoluta_icono_cerrar = obtener_texto(fila, 6)
        ruta_relativa_icono_cerrar = obtener_texto(fila, 7)
        ruta_final_icono_cerrar = resolver_ruta_hibrida(ruta_absoluta_icono_cerrar, ruta_relativa_icono_cerrar)
        self.lineEdit_icono_cerrar.setText(ruta_final_icono_cerrar)
        
        self.lineEdit_hero_titulo.setText(obtener_texto(fila, 8))
        
        ruta_absoluta_hero = obtener_texto(fila, 9)
        ruta_relativa_hero = obtener_texto(fila, 10)
        ruta_final_hero = resolver_ruta_hibrida(ruta_absoluta_hero, ruta_relativa_hero)
        self.lineEdit_hero_imagen.setText(ruta_final_hero)

        self.lineEdit_footer_texto.setText(obtener_texto(fila, 11))
        self.lineEdit_direccion_facebook.setText(obtener_texto(fila, 12))
        self.lineEdit_direccion_instagram.setText(obtener_texto(fila, 13))
        self.lineEdit_direccion_twitter.setText(obtener_texto(fila, 14))
        self.lineEdit_direccion_youtube.setText(obtener_texto(fila, 15))
        self.lineEdit_direccion_correo.setText(obtener_texto(fila, 16))

        # ✅ MEJORADO: Mostrar imágenes con logs detallados
        print("🖼️  Cargando imágenes para configuración inactiva...")
        self.mostrar_imagen_config(ruta_final_logo, self.label_logo_app, 50)
        self.mostrar_imagen_config(ruta_final_icono_abrir, self.label_icono_abrir, 50)
        self.mostrar_imagen_config(ruta_final_icono_cerrar, self.label_icono_cerrar, 50)
        self.mostrar_imagen_config(ruta_final_hero, self.label_imagen_central, 100)

        # Ajustar botones
        self.btnAgregarConfig.setEnabled(False)
        self.btnModificarConfig.setEnabled(False)
        self.btnDesactivarConfig.setEnabled(False)
        self.btnReactivarConfiguracion.setEnabled(True)

        print(f"✅ Configuración inactiva {self.config_inactiva_id} cargada exitosamente")

    def mostrar_imagen_config(self, ruta_imagen: str, label: QLabel, size: int):
        """
        ✅ MEJORADO: Muestra imágenes desde URL remota o archivo local con logs
        """
        print(f"🖼️  Mostrando imagen en label: {ruta_imagen}")
        
        if not ruta_imagen:
            label.clear()
            label.setText("Sin imagen")
            print("⚠️  Ruta de imagen vacía")
            return

        # ✅ USAR la función mejorada cargar_imagen_desde_ruta
        pixmap = cargar_imagen_desde_ruta(ruta_imagen, (size, size))
        if pixmap and not pixmap.isNull():
            pixmap_redondeada = self.redondear_imagen_pixmap(pixmap, size)
            label.setPixmap(pixmap_redondeada)
            label.setText("")
            label.setToolTip(f"Imagen: {ruta_imagen}")
            print(f"✅ Imagen mostrada exitosamente: {ruta_imagen}")
        else:
            label.clear()
            label.setText("Sin imagen")
            label.setToolTip("")
            print(f"❌ No se pudo cargar imagen: {ruta_imagen}")

    def redondear_imagen_pixmap(self, pixmap: QPixmap, size: int) -> QPixmap:
        """
        Redondea un QPixmap ya cargado (para imágenes remotas y locales)
        """
        if pixmap.isNull():
            return QPixmap()

        # Escalar la imagen
        pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        # Crear máscara circular
        mask = QPixmap(size, size)
        mask.fill(Qt.transparent)
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        
        return mask
        
    def agregar_configuracion(self):
        titulo = self.lineEdit_titulo_app.text().strip()
        logo = self.lineEdit_logo_app.text().strip()
        icono_abrir = self.lineEdit_icono_abrir.text().strip()
        icono_cerrar = self.lineEdit_icono_cerrar.text().strip()
        hero_titulo = self.lineEdit_hero_titulo.text().strip()
        hero_img = self.lineEdit_hero_imagen.text().strip()
        footer = self.lineEdit_footer_texto.text().strip()
        facebook = self.lineEdit_direccion_facebook.text().strip()
        instagram = self.lineEdit_direccion_instagram.text().strip()
        twitter = self.lineEdit_direccion_twitter.text().strip()
        youtube = self.lineEdit_direccion_youtube.text().strip()
        correo = self.lineEdit_direccion_correo.text().strip()

        if not titulo or not logo or not icono_abrir or not icono_cerrar or not hero_titulo or not footer:
            QMessageBox.warning(self, "Campos obligatorios", "Debes completar todos los campos requeridos.")
            return

        # ✅ CORREGIDO: Guardar ABSOLUTA en campos principales y RELATIVA en campos _ruta_relativa
        logo_abs = logo
        logo_rel = convertir_ruta_produccion(logo) if not _is_url(logo) else ""
        
        icono_abrir_abs = icono_abrir
        icono_abrir_rel = convertir_ruta_produccion(icono_abrir) if not _is_url(icono_abrir) else ""
        
        icono_cerrar_abs = icono_cerrar
        icono_cerrar_rel = convertir_ruta_produccion(icono_cerrar) if not _is_url(icono_cerrar) else ""
        
        hero_img_abs = hero_img
        hero_img_rel = convertir_ruta_produccion(hero_img) if not _is_url(hero_img) else ""

        # --- CONVERTIR IMÁGENES A BASE64 (solo si son archivos locales) ---
        logo_base64 = imagen_a_base64(logo) if logo and os.path.exists(logo) else None
        icono_abrir_base64 = imagen_a_base64(icono_abrir) if icono_abrir and os.path.exists(icono_abrir) else None
        icono_cerrar_base64 = imagen_a_base64(icono_cerrar) if icono_cerrar and os.path.exists(icono_cerrar) else None
        hero_img_base64 = imagen_a_base64(hero_img) if hero_img and os.path.exists(hero_img) else None

        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO configuracion_app 
                (titulo_app, 
                logo_app, logo_app_ruta_relativa, logo_base64,
                icono_hamburguesa, icono_hamburguesa_ruta_relativa, icono_hamburguesa_base64,
                icono_cerrar, icono_cerrar_ruta_relativa, icono_cerrar_base64,
                hero_titulo, hero_imagen, hero_imagen_ruta_relativa, hero_imagen_base64,
                footer_texto, direccion_facebook, direccion_instagram,
                direccion_twitter, direccion_youtube, correo_electronico, habilitar)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
            """, (
                titulo, 
                logo_abs, logo_rel, logo_base64,
                icono_abrir_abs, icono_abrir_rel, icono_abrir_base64,
                icono_cerrar_abs, icono_cerrar_rel, icono_cerrar_base64,
                hero_titulo, hero_img_abs, hero_img_rel, hero_img_base64,
                footer, facebook, instagram, twitter, youtube, correo
            ))
            conexion.commit()
            conexion.close()

            QMessageBox.information(self, "Configuración", "Configuración agregada correctamente.")
            self.cargar_configuracion_activa()
            self.cargar_configuracion_inactiva()
            self.limpiar_formulario()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo agregar configuración:\n{str(e)}")
            
    def modificar_configuracion(self):
        if not hasattr(self, 'config_seleccionada_id') or not self.config_seleccionada_id:
            QMessageBox.warning(self, "Modificar", "Seleccione una configuración para modificar.")
            return

        logo = self.lineEdit_logo_app.text().strip()
        icono_abrir = self.lineEdit_icono_abrir.text().strip()
        icono_cerrar = self.lineEdit_icono_cerrar.text().strip()
        hero_img = self.lineEdit_hero_imagen.text().strip()
        
        logo_abs = logo
        logo_rel = convertir_ruta_produccion(logo) if not _is_url(logo) else ""
        
        icono_abrir_abs = icono_abrir
        icono_abrir_rel = convertir_ruta_produccion(icono_abrir) if not _is_url(icono_abrir) else ""
        
        icono_cerrar_abs = icono_cerrar
        icono_cerrar_rel = convertir_ruta_produccion(icono_cerrar) if not _is_url(icono_cerrar) else ""
        
        hero_img_abs = hero_img
        hero_img_rel = convertir_ruta_produccion(hero_img) if not _is_url(hero_img) else ""

        # --- CONVERTIR IMÁGENES A BASE64 (solo si son archivos locales) ---
        logo_base64 = imagen_a_base64(logo) if logo and os.path.exists(logo) else None
        icono_abrir_base64 = imagen_a_base64(icono_abrir) if icono_abrir and os.path.exists(icono_abrir) else None
        icono_cerrar_base64 = imagen_a_base64(icono_cerrar) if icono_cerrar and os.path.exists(icono_cerrar) else None
        hero_img_base64 = imagen_a_base64(hero_img) if hero_img and os.path.exists(hero_img) else None

        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE configuracion_app
                SET titulo_app=%s,
                    logo_app=%s, logo_app_ruta_relativa=%s, logo_base64=%s,
                    icono_hamburguesa=%s, icono_hamburguesa_ruta_relativa=%s, icono_hamburguesa_base64=%s,
                    icono_cerrar=%s, icono_cerrar_ruta_relativa=%s, icono_cerrar_base64=%s,
                    hero_titulo=%s, hero_imagen=%s, hero_imagen_ruta_relativa=%s, hero_imagen_base64=%s,
                    footer_texto=%s,
                    direccion_facebook=%s,
                    direccion_instagram=%s,
                    direccion_twitter=%s,
                    direccion_youtube=%s,
                    correo_electronico=%s
                WHERE id_config=%s
            """, (
                self.lineEdit_titulo_app.text(),
                logo_abs, logo_rel, logo_base64,
                icono_abrir_abs, icono_abrir_rel, icono_abrir_base64,
                icono_cerrar_abs, icono_cerrar_rel, icono_cerrar_base64,
                self.lineEdit_hero_titulo.text(),
                hero_img_abs, hero_img_rel, hero_img_base64,
                self.lineEdit_footer_texto.text(),
                self.lineEdit_direccion_facebook.text(),
                self.lineEdit_direccion_instagram.text(),
                self.lineEdit_direccion_twitter.text(),
                self.lineEdit_direccion_youtube.text(),
                self.lineEdit_direccion_correo.text(),
                self.config_seleccionada_id
            ))
            conexion.commit()
            conexion.close()

            QMessageBox.information(self, "Configuración", "Configuración modificada correctamente.")
            self.cargar_configuracion_activa()
            self.cargar_configuracion_inactiva()
            self.limpiar_formulario()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo modificar configuración:\n{str(e)}")

    def desactivar_configuracion(self):
        if not hasattr(self, 'config_seleccionada_id') or not self.config_seleccionada_id:
            QMessageBox.warning(self, "Desactivar", "Seleccione una configuración para desactivar.")
            return

        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("UPDATE configuracion_app SET habilitar=0 WHERE id_config=%s", (self.config_seleccionada_id,))
            conexion.commit()
            conexion.close()

            QMessageBox.information(self, "Configuración", "Configuración desactivada correctamente.")
            self.cargar_configuracion_activa()
            self.cargar_configuracion_inactiva()
            self.limpiar_formulario()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo desactivar configuración:\n{str(e)}")

    def reactivar_configuracion(self):
        if not hasattr(self, 'config_inactiva_id') or not self.config_inactiva_id:
            QMessageBox.warning(self, "Reactivar", "Seleccione una configuración inactiva.")
            return

        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("UPDATE configuracion_app SET habilitar=1 WHERE id_config=%s", (self.config_inactiva_id,))
            conexion.commit()
            conexion.close()

            QMessageBox.information(self, "Configuración", "Configuración reactivada correctamente.")
            self.cargar_configuracion_activa()
            self.cargar_configuracion_inactiva()
            self.config_inactiva_id = None
            self.btnReactivarConfiguracion.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo reactivar configuración:\n{str(e)}")

    def limpiar_formulario(self):
        self.lineEdit_titulo_app.clear()
        self.lineEdit_logo_app.clear()
        self.lineEdit_icono_abrir.clear()
        self.lineEdit_icono_cerrar.clear()
        self.lineEdit_hero_titulo.clear()
        self.lineEdit_hero_imagen.clear()
        self.lineEdit_footer_texto.clear()
        self.lineEdit_direccion_facebook.clear()
        self.lineEdit_direccion_instagram.clear()
        self.lineEdit_direccion_twitter.clear()
        self.lineEdit_direccion_youtube.clear()
        self.lineEdit_direccion_correo.clear()
        
        self.label_imagen_central.clear()
        self.label_imagen_central.setText("Sin imagen")
        self.label_logo_app.clear()
        self.label_icono_abrir.clear()
        self.label_icono_cerrar.clear()
        self.label_logo_app.setText("Sin imagen")
        self.label_icono_abrir.setText("Sin imagen")
        self.label_icono_cerrar.setText("Sin imagen")

        self.config_seleccionada_id = None
        self.config_inactiva_id = None

        self.btnAgregarConfig.setEnabled(True)
        self.btnModificarConfig.setEnabled(False)
        self.btnDesactivarConfig.setEnabled(False)
        self.btnReactivarConfiguracion.setEnabled(False)

    # ------------------ Imagenes -------------------
    
    def seleccionar_media(self, titulo_dialogo):
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            titulo_dialogo,
            "",
            "Archivos Multimedia (*.jpg *.jpeg *.png *.webp *.bmp *.gif *.webm *.mp4)"
        )
        return ruta if ruta else None



    def seleccionar_logo(self):
        ruta = self.seleccionar_media("Seleccionar logo")
        if not ruta:
            return

        ruta_relativa = convertir_ruta_produccion(ruta)

        self.lineEdit_logo_app.setText(ruta)
        self.mostrar_imagen_config(ruta, self.label_logo_app, 50)

        if self.config_seleccionada_id:
            try:
                conexion = conectar_base_datos()
                cursor = conexion.cursor()
                cursor.execute("""
                    UPDATE configuracion_app
                    SET logo_app=%s,
                        logo_app_ruta_relativa=%s,
                        logo_base64=%s
                    WHERE id_config=%s
                """, (
                    ruta,
                    ruta_relativa,
                    imagen_a_base64(ruta),
                    self.config_seleccionada_id
                ))
                conexion.commit()
                conexion.close()
                self.cargar_configuracion_activa()
            except Exception as e:
                QMessageBox.warning(self, "Error BD", f"No se pudo actualizar el logo:\n{e}")



    def seleccionar_icono_abrir(self):
        ruta = self.seleccionar_media("Seleccionar icono abrir")
        if not ruta:
            return

        ruta_relativa = convertir_ruta_produccion(ruta)

        self.lineEdit_icono_abrir.setText(ruta)
        self.mostrar_imagen_config(ruta, self.label_icono_abrir, 50)

        if self.config_seleccionada_id:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE configuracion_app
                SET icono_hamburguesa=%s,
                    icono_hamburguesa_ruta_relativa=%s,
                    icono_hamburguesa_base64=%s
                WHERE id_config=%s
            """, (
                ruta,
                ruta_relativa,
                imagen_a_base64(ruta),
                self.config_seleccionada_id
            ))
            conexion.commit()
            conexion.close()
            self.cargar_configuracion_activa()



    def seleccionar_icono_cerrar(self):
        ruta = self.seleccionar_media("Seleccionar icono cerrar")
        if not ruta:
            return

        ruta_relativa = convertir_ruta_produccion(ruta)

        self.lineEdit_icono_cerrar.setText(ruta)
        self.mostrar_imagen_config(ruta, self.label_icono_cerrar, 50)

        if self.config_seleccionada_id:
            try:
                conexion = conectar_base_datos()
                cursor = conexion.cursor()
                cursor.execute("""
                    UPDATE configuracion_app
                    SET icono_cerrar=%s,
                        icono_cerrar_ruta_relativa=%s,
                        icono_cerrar_base64=%s
                    WHERE id_config=%s
                """, (
                    ruta,
                    ruta_relativa,
                    imagen_a_base64(ruta),
                    self.config_seleccionada_id
                ))
                conexion.commit()
                conexion.close()
                self.cargar_configuracion_activa()
            except Exception as e:
                QMessageBox.warning(self, "Error BD", f"No se pudo actualizar el icono:\n{e}")



    def seleccionar_hero_imagen(self):
        ruta = self.seleccionar_media("Seleccionar imagen o video principal")
        if not ruta:
            return

        ruta_relativa = convertir_ruta_produccion(ruta)

        self.lineEdit_hero_imagen.setText(ruta)

        # 🔥 SI ES VIDEO → no intentar mostrar como imagen
        if es_video(ruta):
            self.label_imagen_central.clear()
            self.label_imagen_central.setText("🎥 Video seleccionado")
        else:
            self.mostrar_imagen_config(ruta, self.label_imagen_central, 100)

        hero_base64 = None
        if not es_video(ruta) and os.path.exists(ruta):
            hero_base64 = imagen_a_base64(ruta)

        if self.config_seleccionada_id:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE configuracion_app
                SET hero_imagen=%s,
                    hero_imagen_ruta_relativa=%s,
                    hero_imagen_base64=%s
                WHERE id_config=%s
            """, (
                ruta,
                ruta_relativa,
                hero_base64,
                self.config_seleccionada_id
            ))
            conexion.commit()
            conexion.close()
            self.cargar_configuracion_activa()
