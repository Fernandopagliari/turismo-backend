# -*- coding: utf-8 -*-
import base64
import os
import requests
from PyQt5 import uic
from database_hosting import conectar_hosting as conectar_base_datos
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QApplication, QWidget, QMessageBox, QLabel
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush, QPen, QColor, QPainterPath
from PyQt5.QtCore import Qt

def imagen_a_base64(ruta_imagen):
    """Convierte imagen a Base64 para guardar en BD"""
    try:
        with open(ruta_imagen, "rb") as file:
            image_data = file.read()
            base64_encoded = base64.b64encode(image_data).decode('utf-8')
            return f"data:image/jpeg;base64,{base64_encoded}"
    except Exception as e:
        print(f"Error procesando imagen: {e}")
        return None

def convertir_ruta_produccion(ruta_absoluta):
    """Convierte rutas absolutas a rutas relativas - VERSIÓN FINAL"""
    from PyQt5.QtWidgets import QMessageBox
    
    if not ruta_absoluta or not os.path.exists(ruta_absoluta):
        return ""
    
    ruta_normalizada = os.path.normpath(ruta_absoluta)
    
    # Buscar "assets/imagenes"
    target = "assets" + os.sep + "imagenes" + os.sep
    idx = ruta_normalizada.lower().find(target.lower())
    
    if idx != -1:
        ruta_relativa = ruta_normalizada[idx + len(target):]
        # ✅ NORMALIZAR a barras simples para web
        resultado = f"assets/imagenes/{ruta_relativa}".replace("\\", "/")
        return resultado
    
    nombre_archivo = os.path.basename(ruta_absoluta)
    resultado = f"assets/imagenes/{nombre_archivo}"
    return resultado

# -------------------------
# NUEVOS MÉTODOS PARA COMPATIBILIDAD CON VENTANA_PRINCIPAL
# -------------------------
def _is_url(path):
    """Verifica si una ruta es una URL"""
    return isinstance(path, str) and (path.startswith("http://") or path.startswith("https://"))

def obtener_url_remota(ruta_relativa: str) -> str:
    """Construye URL remota basada en la configuración de hosting"""
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
                ruta_limpia = ruta_relativa.lstrip('/')
                url_completa = f"{base_url}assets/{ruta_limpia}"
                return url_completa
    except Exception as e:
        print(f"Error obteniendo URL remota: {e}")
    return ""

def verificar_url_remota(url: str) -> bool:
    """Verifica si una URL remota es accesible"""
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def resolver_ruta_hibrida(ruta_absoluta_db: str, ruta_relativa_db: str) -> str:
    """
    Busca imágenes en REMOTO → LOCAL (igual que ventana_principal)
    """
    # 1. PRIMERO: Buscar en REMOTO usando ruta relativa
    if ruta_relativa_db:
        url_remota = obtener_url_remota(ruta_relativa_db)
        if url_remota and verificar_url_remota(url_remota):
            print(f"✅ [CONFIG] Encontrado en REMOTO: {url_remota}")
            return url_remota
    
    # 2. SEGUNDO: Buscar en LOCAL con ruta absoluta
    if ruta_absoluta_db and os.path.exists(ruta_absoluta_db):
        print(f"✅ [CONFIG] Encontrado en LOCAL: {ruta_absoluta_db}")
        return ruta_absoluta_db
    
    # 3. TERCERO: Buscar en estructura del proyecto
    if ruta_relativa_db:
        rutas_posibles = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                        "turismo-frontend", "public", ruta_relativa_db),
            os.path.join(os.getcwd(), "turismo-frontend", "public", ruta_relativa_db),
        ]
        
        for ruta in rutas_posibles:
            if os.path.exists(ruta):
                print(f"✅ [CONFIG] Encontrado en PROYECTO: {ruta}")
                return ruta
    
    print(f"❌ [CONFIG] No encontrado: {ruta_relativa_db}")
    return ""

def cargar_imagen_desde_ruta(ruta_imagen: str, label: QLabel, size: int):
    """
    Carga imagen desde URL remota o archivo local y la muestra en el QLabel
    """
    if not ruta_imagen:
        label.clear()
        label.setText("Sin imagen")
        return None

    try:
        # ✅ MANEJAR URL REMOTA
        if _is_url(ruta_imagen):
            response = requests.get(ruta_imagen, timeout=10)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                if not pixmap.isNull():
                    print(f"✅ [CONFIG] Imagen remota cargada: {ruta_imagen}")
                    return pixmap
            return None
        
        # ✅ MANEJAR ARCHIVO LOCAL
        elif os.path.exists(ruta_imagen):
            pixmap = QPixmap(ruta_imagen)
            if not pixmap.isNull():
                print(f"✅ [CONFIG] Imagen local cargada: {ruta_imagen}")
                return pixmap
        
        return None
        
    except Exception as e:
        print(f"❌ [CONFIG] Error cargando imagen: {e}")
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

    # ------------------ CRUD -------------------

    def cargar_configuracion_activa(self):
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
                item = QTableWidgetItem(str(data))
                self.Tabla_configuracion_activa.setItem(row_number, column_number, item)

    def cargar_configuracion_inactiva(self):
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
                item = QTableWidgetItem(str(data))
                self.Tabla_configuraciones_inactiva.setItem(row_number, column_number, item)
                
    def seleccionar_config_activa(self, fila, columna):
        def obtener_texto(f, c):
            item = self.Tabla_configuracion_activa.item(f, c)
            return item.text() if item else ""

        # --- NUEVO: Usar búsqueda híbrida REMOTO → LOCAL ---
        self.config_seleccionada_id = obtener_texto(fila, 0)
        self.lineEdit_titulo_app.setText(obtener_texto(fila, 1))
        
        # ✅ BUSQUEDA HÍBRIDA para todas las imágenes
        self.lineEdit_logo_app.setText(
            resolver_ruta_hibrida(obtener_texto(fila, 2), obtener_texto(fila, 3))
        )
        self.lineEdit_icono_abrir.setText(
            resolver_ruta_hibrida(obtener_texto(fila, 4), obtener_texto(fila, 5))
        )
        self.lineEdit_icono_cerrar.setText(
            resolver_ruta_hibrida(obtener_texto(fila, 6), obtener_texto(fila, 7))
        )
        self.lineEdit_hero_titulo.setText(obtener_texto(fila, 8))
        self.lineEdit_hero_imagen.setText(
            resolver_ruta_hibrida(obtener_texto(fila, 9), obtener_texto(fila, 10))
        )
        self.lineEdit_footer_texto.setText(obtener_texto(fila, 11))
        self.lineEdit_direccion_facebook.setText(obtener_texto(fila, 12))
        self.lineEdit_direccion_instagram.setText(obtener_texto(fila, 13))
        self.lineEdit_direccion_twitter.setText(obtener_texto(fila, 14))
        self.lineEdit_direccion_youtube.setText(obtener_texto(fila, 15))
        self.lineEdit_direccion_correo.setText(obtener_texto(fila, 16))

        # --- Mostrar imágenes con soporte para URLs remotas ---
        self.mostrar_imagen_config(self.lineEdit_logo_app.text(), self.label_logo_app, 50)
        self.mostrar_imagen_config(self.lineEdit_icono_abrir.text(), self.label_icono_abrir, 50)
        self.mostrar_imagen_config(self.lineEdit_icono_cerrar.text(), self.label_icono_cerrar, 50)
        self.mostrar_imagen_config(self.lineEdit_hero_imagen.text(), self.label_imagen_central, 100)

        # --- Botones ---
        self.btnAgregarConfig.setEnabled(False)
        self.btnModificarConfig.setEnabled(True)
        self.btnDesactivarConfig.setEnabled(True)
        self.btnReactivarConfiguracion.setEnabled(False)

    def seleccionar_config_inactiva(self, fila, columna):
        def obtener_texto(f, c):
            item = self.Tabla_configuraciones_inactiva.item(f, c)
            return item.text() if item else ""

        # ✅ USAR BUSQUEDA HÍBRIDA también para configuraciones inactivas
        self.config_inactiva_id = obtener_texto(fila, 0)
        self.lineEdit_titulo_app.setText(obtener_texto(fila, 1))
        
        self.lineEdit_logo_app.setText(
            resolver_ruta_hibrida(obtener_texto(fila, 2), obtener_texto(fila, 3))
        )
        self.lineEdit_icono_abrir.setText(
            resolver_ruta_hibrida(obtener_texto(fila, 4), obtener_texto(fila, 5))
        )
        self.lineEdit_icono_cerrar.setText(
            resolver_ruta_hibrida(obtener_texto(fila, 6), obtener_texto(fila, 7))
        )
        self.lineEdit_hero_titulo.setText(obtener_texto(fila, 8))
        self.lineEdit_hero_imagen.setText(
            resolver_ruta_hibrida(obtener_texto(fila, 9), obtener_texto(fila, 10))
        )
        self.lineEdit_footer_texto.setText(obtener_texto(fila, 11))
        self.lineEdit_direccion_facebook.setText(obtener_texto(fila, 12))
        self.lineEdit_direccion_instagram.setText(obtener_texto(fila, 13))
        self.lineEdit_direccion_twitter.setText(obtener_texto(fila, 14))
        self.lineEdit_direccion_youtube.setText(obtener_texto(fila, 15))
        self.lineEdit_direccion_correo.setText(obtener_texto(fila, 16))

        # --- Mostrar imágenes con soporte para URLs remotas ---
        self.mostrar_imagen_config(self.lineEdit_logo_app.text(), self.label_logo_app, 50)
        self.mostrar_imagen_config(self.lineEdit_icono_abrir.text(), self.label_icono_abrir, 50)
        self.mostrar_imagen_config(self.lineEdit_icono_cerrar.text(), self.label_icono_cerrar, 50)
        self.mostrar_imagen_config(self.lineEdit_hero_imagen.text(), self.label_imagen_central, 100)

        # --- Ajustar botones ---
        self.btnAgregarConfig.setEnabled(False)
        self.btnModificarConfig.setEnabled(False)
        self.btnDesactivarConfig.setEnabled(False)
        self.btnReactivarConfiguracion.setEnabled(True)

    def mostrar_imagen_config(self, ruta_imagen: str, label: QLabel, size: int):
        """
        NUEVO: Muestra imágenes desde URL remota o archivo local en configuración
        """
        if not ruta_imagen:
            label.clear()
            label.setText("Sin imagen")
            return

        pixmap = cargar_imagen_desde_ruta(ruta_imagen, label, size)
        if pixmap and not pixmap.isNull():
            pixmap_redondeada = self.redondear_imagen_pixmap(pixmap, size)
            label.setPixmap(pixmap_redondeada)
            label.setText("")
        else:
            label.clear()
            label.setText("Sin imagen")

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
        self.label_imagen_central.setText("Sin foto")
        self.label_logo_app.clear()
        self.label_icono_abrir.clear()
        self.label_icono_cerrar.clear()
        self.label_logo_app.setText("")
        self.label_icono_abrir.setText("")
        self.label_icono_cerrar.setText("")

        self.config_seleccionada_id = None
        self.config_inactiva_id = None

        self.btnAgregarConfig.setEnabled(True)
        self.btnModificarConfig.setEnabled(False)
        self.btnDesactivarConfig.setEnabled(False)
        self.btnReactivarConfiguracion.setEnabled(False)

    # ------------------ Imagenes -------------------

    def seleccionar_logo(self):
        ruta_absoluta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar logo", "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if not ruta_absoluta:
            return

        ruta_relativa = convertir_ruta_produccion(ruta_absoluta)
        
        self.lineEdit_logo_app.setText(ruta_absoluta)

        if os.path.exists(ruta_absoluta):
            pixmap_logo = self.redondear_imagen(ruta_absoluta, size=50)
            self.label_logo_app.setPixmap(pixmap_logo)
            self.label_logo_app.setText("")

        if hasattr(self, 'config_seleccionada_id') and self.config_seleccionada_id:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE configuracion_app
                SET logo_app=%s, logo_app_ruta_relativa=%s, logo_base64=%s
                WHERE id_config=%s
            """, (ruta_absoluta, ruta_relativa, imagen_a_base64(ruta_absoluta), self.config_seleccionada_id))
            conexion.commit()
            conexion.close()

    def seleccionar_icono_abrir(self):
        ruta_absoluta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar icono abrir", "", "Iconos (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not ruta_absoluta:
            return

        ruta_relativa = convertir_ruta_produccion(ruta_absoluta)

        self.lineEdit_icono_abrir.setText(ruta_absoluta)

        if os.path.exists(ruta_absoluta):
            pixmap_icono = self.redondear_imagen(ruta_absoluta, size=50)
            self.label_icono_abrir.setPixmap(pixmap_icono)
            self.label_icono_abrir.setText("")

        if hasattr(self, 'config_seleccionada_id') and self.config_seleccionada_id:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE configuracion_app
                SET icono_hamburguesa=%s, icono_hamburguesa_ruta_relativa=%s, icono_hamburguesa_base64=%s
                WHERE id_config=%s
            """, (ruta_absoluta, ruta_relativa, imagen_a_base64(ruta_absoluta), self.config_seleccionada_id))
            conexion.commit()
            conexion.close()

    def seleccionar_icono_cerrar(self):
        ruta_absoluta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar icono cerrar", "", "Iconos (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not ruta_absoluta:
            return

        ruta_relativa = convertir_ruta_produccion(ruta_absoluta)

        self.lineEdit_icono_cerrar.setText(ruta_absoluta)

        if os.path.exists(ruta_absoluta):
            pixmap_icono = self.redondear_imagen(ruta_absoluta, size=50)
            self.label_icono_cerrar.setPixmap(pixmap_icono)
            self.label_icono_cerrar.setText("")

        if hasattr(self, 'config_seleccionada_id') and self.config_seleccionada_id:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE configuracion_app
                SET icono_cerrar=%s, icono_cerrar_ruta_relativa=%s, icono_cerrar_base64=%s
                WHERE id_config=%s
            """, (ruta_absoluta, ruta_relativa, imagen_a_base64(ruta_absoluta), self.config_seleccionada_id))
            conexion.commit()
            conexion.close()

    def seleccionar_hero_imagen(self):
        ruta_absoluta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen principal", "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not ruta_absoluta:
            return

        ruta_relativa = convertir_ruta_produccion(ruta_absoluta)

        self.lineEdit_hero_imagen.setText(ruta_absoluta)

        if os.path.exists(ruta_absoluta):
            pixmap_hero = self.redondear_imagen(ruta_absoluta, size=100)
            self.label_imagen_central.setPixmap(pixmap_hero)
            self.label_imagen_central.setText("")

        if hasattr(self, 'config_seleccionada_id') and self.config_seleccionada_id:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE configuracion_app
                SET hero_imagen=%s, hero_imagen_ruta_relativa=%s, hero_imagen_base64=%s
                WHERE id_config=%s
            """, (ruta_absoluta, ruta_relativa, imagen_a_base64(ruta_absoluta), self.config_seleccionada_id))
            conexion.commit()
            conexion.close()

    def redondear_imagen(self, ruta_imagen, size: int = None):
        """
        Carga una imagen desde ruta y la redondea
        """
        if not ruta_imagen:
            return QPixmap()

        pixmap = QPixmap(ruta_imagen)
        if pixmap.isNull():
            return QPixmap()

        if size is None:
            size = 100

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