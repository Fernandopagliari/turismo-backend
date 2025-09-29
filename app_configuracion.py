# -*- coding: utf-8 -*-
from PyQt5 import uic
from database import conectar_base_datos
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QApplication, QWidget, QMessageBox, QLabel
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush, QPen, QColor, QPainterPath
from PyQt5.QtCore import Qt
import os



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
            SELECT id_config, titulo_app, logo_app, icono_hamburguesa, icono_cerrar, hero_titulo, hero_imagen, footer_texto, direccion_facebook, direccion_instagram, direccion_twitter, direccion_youtube, correo_electronico
            FROM configuracion_app WHERE habilitar = 1
        """)
        resultados = cursor.fetchall()
        conexion.close()

        columnas = ["ID", "Título", "Logo", "Icono Abrir", "Icono Cerrar", "Hero Título", "Hero Imagen", "Footer", "Facebook", "Instagram", "Twitter", "Youtube", "Correo Electrónico"]
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
            SELECT id_config, titulo_app, logo_app, icono_hamburguesa, icono_cerrar, hero_titulo, hero_imagen, footer_texto, direccion_facebook, direccion_instagram, direccion_twitter, direccion_youtube, correo_electronico
            FROM configuracion_app WHERE habilitar = 0
        """)
        resultados = cursor.fetchall()
        conexion.close()

        columnas = ["ID", "Título", "Logo", "Icono Abrir", "Icono Cerrar", "Hero Título", "Hero Imagen", "Footer", "Facebook", "Instagram", "Twitter", "Youtube", "Correo Electrónico"]
        self.Tabla_configuraciones_inactiva.setColumnCount(len(columnas))
        self.Tabla_configuraciones_inactiva.setHorizontalHeaderLabels(columnas)
        self.Tabla_configuraciones_inactiva.setRowCount(0)

        for row_number, row_data in enumerate(resultados):
            self.Tabla_configuraciones_inactiva.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                item = QTableWidgetItem(str(data))
                self.Tabla_configuraciones_inactiva.setItem(row_number, column_number, item)

    def seleccionar_config_activa(self, fila, columna):
        import os

        def obtener_texto(f, c):
            item = self.Tabla_configuracion_activa.item(f, c)
            return item.text() if item else ""

        # --- Helper: convertir rutas relativas de la DB a absolutas si es necesario ---
        def ruta_absoluta(ruta_absoluta_o_relativa: str, ruta_relativa_db: str):
            """
            Si la ruta absoluta existe, la devuelve.
            Si no, intenta construirla desde la ruta relativa almacenada en la DB.
            """
            if ruta_absoluta_o_relativa and os.path.exists(ruta_absoluta_o_relativa):
                return ruta_absoluta_o_relativa
            # Construir desde ruta relativa
            if ruta_relativa_db:
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                abs_path = os.path.join(base_dir, ruta_relativa_db.lstrip("/\\"))
                if os.path.exists(abs_path):
                    return abs_path
            return ""

        # --- Guardar valores en lineEdits (solo mostrar rutas absolutas) ---
        self.config_seleccionada_id = obtener_texto(fila, 0)
        self.lineEdit_titulo_app.setText(obtener_texto(fila, 1))
        self.lineEdit_logo_app.setText(ruta_absoluta(obtener_texto(fila, 2), obtener_texto(fila, 3)))
        self.lineEdit_icono_abrir.setText(ruta_absoluta(obtener_texto(fila, 3), obtener_texto(fila, 4)))
        self.lineEdit_icono_cerrar.setText(ruta_absoluta(obtener_texto(fila, 4), obtener_texto(fila, 5)))
        self.lineEdit_hero_titulo.setText(obtener_texto(fila, 5))
        self.lineEdit_hero_imagen.setText(ruta_absoluta(obtener_texto(fila, 6), obtener_texto(fila, 7)))
        self.lineEdit_footer_texto.setText(obtener_texto(fila, 7))
        self.lineEdit_direccion_facebook.setText(obtener_texto(fila, 8))
        self.lineEdit_direccion_instagram.setText(obtener_texto(fila, 9))
        self.lineEdit_direccion_twitter.setText(obtener_texto(fila, 10))
        self.lineEdit_direccion_youtube.setText(obtener_texto(fila, 11))
        self.lineEdit_direccion_correo.setText(obtener_texto(fila, 12))
        # --- Mostrar LOGO ---
        ruta_logo = self.lineEdit_logo_app.text()
        if ruta_logo:
            pixmap_logo = self.redondear_imagen(ruta_logo, size=47)
            self.label_logo_app.setPixmap(pixmap_logo)
        else:
            self.label_logo_app.clear()
            self.label_logo_app.setText("Sin logo")

        # --- Mostrar ICONO Abrir ---
        ruta_icono_abrir = self.lineEdit_icono_abrir.text()
        if ruta_icono_abrir:
            pixmap_icono1 = self.redondear_imagen(ruta_icono_abrir, size=47)
            self.label_icono_abrir.setPixmap(pixmap_icono1)
        else:
            self.label_icono_abrir.clear()
            self.label_icono_abrir.setText("Sin icono")

        # --- Mostrar ICONO Cerrar ---
        ruta_icono_cerrar = self.lineEdit_icono_cerrar.text()
        if ruta_icono_cerrar:
            pixmap_icono2 = self.redondear_imagen(ruta_icono_cerrar, size=47)
            self.label_icono_cerrar.setPixmap(pixmap_icono2)
        else:
            self.label_icono_cerrar.clear()
            self.label_icono_cerrar.setText("Sin icono")

        # --- Mostrar HERO IMAGEN ---
        ruta_hero = self.lineEdit_hero_imagen.text()
        if ruta_hero:
            pixmap_hero = self.redondear_imagen(ruta_hero, size=100)
            self.label_imagen_central.setPixmap(pixmap_hero)
        else:
            self.label_imagen_central.clear()
            self.label_imagen_central.setText("Sin foto")

        # --- Botones ---
        self.btnAgregarConfig.setEnabled(False)
        self.btnModificarConfig.setEnabled(True)
        self.btnDesactivarConfig.setEnabled(True)
        self.btnReactivarConfiguracion.setEnabled(False)

        # --- Ajustar tamaño fijo de labels ---
        self.label_logo_app.setFixedSize(50, 50)
        self.label_icono_abrir.setFixedSize(50, 50)
        self.label_icono_cerrar.setFixedSize(50, 50)
        self.label_imagen_central.setFixedSize(100, 100)




    def seleccionar_config_inactiva(self, fila, columna):
        def obtener_texto(f, c):
            item = self.Tabla_configuraciones_inactiva.item(f, c)
            return item.text() if item else ""

        def ruta_absoluta(ruta_relativa):
            if not ruta_relativa:
                return ""
            if os.path.isabs(ruta_relativa) and os.path.exists(ruta_relativa):
                return ruta_relativa
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            abs_path = os.path.join(base_dir, ruta_relativa.lstrip("/\\"))
            return abs_path if os.path.exists(abs_path) else ""

        self.config_inactiva_id = obtener_texto(fila, 0)
        self.lineEdit_titulo_app.setText(obtener_texto(fila, 1))
        self.lineEdit_logo_app.setText(ruta_absoluta(obtener_texto(fila, 2)))
        self.lineEdit_icono_abrir.setText(ruta_absoluta(obtener_texto(fila, 3)))
        self.lineEdit_icono_cerrar.setText(ruta_absoluta(obtener_texto(fila, 4)))
        self.lineEdit_hero_titulo.setText(obtener_texto(fila, 5))
        self.lineEdit_hero_imagen.setText(ruta_absoluta(obtener_texto(fila, 6)))
        self.lineEdit_footer_texto.setText(obtener_texto(fila, 7))
        self.lineEdit_direccion_facebook.setText(obtener_texto(fila, 8))
        self.lineEdit_direccion_instagram.setText(obtener_texto(fila, 9))
        self.lineEdit_direccion_twitter.setText(obtener_texto(fila, 10))
        self.lineEdit_direccion_youtube.setText(obtener_texto(fila, 11))
        self.lineEdit_direccion_correo.setText(obtener_texto(fila, 12))
        

        # --- Mostrar imágenes en QLabel ---
        for label, ruta in [
            (self.label_logo_app, self.lineEdit_logo_app.text()),
            (self.label_icono_abrir, self.lineEdit_icono_abrir.text()),
            (self.label_icono_cerrar, self.lineEdit_icono_cerrar.text()),
            (self.label_imagen_central, self.lineEdit_hero_imagen.text())
        ]:
            if ruta and os.path.exists(ruta):
                pixmap = self.redondear_imagen(ruta, label, circular=True)
                label.setPixmap(pixmap)
            else:
                label.clear()
                label.setText("Sin imagen")

        # --- Ajustar botones ---
        self.btnAgregarConfig.setEnabled(False)
        self.btnModificarConfig.setEnabled(False)
        self.btnDesactivarConfig.setEnabled(False)
        self.btnReactivarConfiguracion.setEnabled(True)

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

        # --- Crear rutas relativas dinámicas ---
        ruta_base = os.path.abspath(os.path.join(os.getcwd(), "public"))
        logo_rel = "/" + os.path.relpath(logo, ruta_base).replace("\\", "/")
        icono_abrir_rel = "/" + os.path.relpath(icono_abrir, ruta_base).replace("\\", "/")
        icono_cerrar_rel = "/" + os.path.relpath(icono_cerrar, ruta_base).replace("\\", "/")
        hero_img_rel = "/" + os.path.relpath(hero_img, ruta_base).replace("\\", "/")

        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO configuracion_app 
                (titulo_app, logo_app, logo_app_ruta_relativa,
                icono_hamburguesa, icono_hamburguesa_ruta_relativa,
                icono_cerrar, icono_cerrar_ruta_relativa,
                hero_titulo, hero_imagen, hero_imagen_ruta_relativa,
                footer_texto, direccion_facebook, direccion_instagram,
                direccion_twitter, direccion_youtube, correo_electronico, habilitar)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
            """, (
                titulo, logo, logo_rel,
                icono_abrir, icono_abrir_rel,
                icono_cerrar, icono_cerrar_rel,
                hero_titulo, hero_img, hero_img_rel,
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

        # --- Crear rutas relativas dinámicas desde la carpeta 'public' ---
        ruta_base = os.path.abspath(os.path.join(os.getcwd(), "public"))
        logo_rel = "/" + os.path.relpath(self.lineEdit_logo_app.text(), ruta_base).replace("\\", "/")
        icono_abrir_rel = "/" + os.path.relpath(self.lineEdit_icono_abrir.text(), ruta_base).replace("\\", "/")
        icono_cerrar_rel = "/" + os.path.relpath(self.lineEdit_icono_cerrar.text(), ruta_base).replace("\\", "/")
        hero_img_rel = "/" + os.path.relpath(self.lineEdit_hero_imagen.text(), ruta_base).replace("\\", "/")

        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE configuracion_app
                SET titulo_app=%s,
                    logo_app=%s, logo_app_ruta_relativa=%s,
                    icono_hamburguesa=%s, icono_hamburguesa_ruta_relativa=%s,
                    icono_cerrar=%s, icono_cerrar_ruta_relativa=%s,
                    hero_titulo=%s, hero_imagen=%s, hero_imagen_ruta_relativa=%s,
                    footer_texto=%s,
                    direccion_facebook=%s,
                    direccion_instagram=%s,
                    direccion_twitter=%s,
                    direccion_youtube=%s,
                    correo_electronico=%s
                WHERE id_config=%s
            """, (
                self.lineEdit_titulo_app.text(),
                self.lineEdit_logo_app.text(), logo_rel,
                self.lineEdit_icono_abrir.text(), icono_abrir_rel,
                self.lineEdit_icono_cerrar.text(), icono_cerrar_rel,
                self.lineEdit_hero_titulo.text(),
                self.lineEdit_hero_imagen.text(), hero_img_rel,
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

        # --- Guardar ruta relativa desde /assets ---
        nombre_archivo = os.path.basename(ruta_absoluta)
        ruta_relativa = f"/assets/iconos/{nombre_archivo}"

        # Mostrar ruta absoluta en QLineEdit
        self.lineEdit_logo_app.setText(ruta_absoluta)

        # Mostrar en QLabel
        if os.path.exists(ruta_absoluta):
            pixmap_logo = self.redondear_imagen(ruta_absoluta, self.label_logo_app, circular=True)
            self.label_logo_app.setPixmap(pixmap_logo)
            self.label_logo_app.setText("")

        # Guardar en DB si ya hay config seleccionada
        if hasattr(self, 'config_seleccionada_id') and self.config_seleccionada_id:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE configuracion_app
                SET logo_app=%s, logo_app_ruta_relativa=%s
                WHERE id_config=%s
            """, (ruta_absoluta, ruta_relativa, self.config_seleccionada_id))
            conexion.commit()
            conexion.close()


    def seleccionar_icono_abrir(self):
        ruta_absoluta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar icono abrir", "", "Iconos (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not ruta_absoluta:
            return

        nombre_archivo = os.path.basename(ruta_absoluta)
        ruta_relativa = f"/assets/iconos/{nombre_archivo}"

        self.lineEdit_icono_abrir.setText(ruta_absoluta)

        if os.path.exists(ruta_absoluta):
            pixmap_icono = self.redondear_imagen(ruta_absoluta, self.label_icono_abrir, circular=True)
            self.label_icono_abrir.setPixmap(pixmap_icono)
            self.label_icono_abrir.setText("")

        if hasattr(self, 'config_seleccionada_id') and self.config_seleccionada_id:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE configuracion_app
                SET icono_hamburguesa=%s, icono_hamburguesa_ruta_relativa=%s
                WHERE id_config=%s
            """, (ruta_absoluta, ruta_relativa, self.config_seleccionada_id))
            conexion.commit()
            conexion.close()


    def seleccionar_icono_cerrar(self):
        ruta_absoluta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar icono cerrar", "", "Iconos (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not ruta_absoluta:
            return

        nombre_archivo = os.path.basename(ruta_absoluta)
        ruta_relativa = f"/assets/iconos/{nombre_archivo}"

        self.lineEdit_icono_cerrar.setText(ruta_absoluta)

        if os.path.exists(ruta_absoluta):
            pixmap_icono = self.redondear_imagen(ruta_absoluta, self.label_icono_cerrar, circular=True)
            self.label_icono_cerrar.setPixmap(pixmap_icono)
            self.label_icono_cerrar.setText("")

        if hasattr(self, 'config_seleccionada_id') and self.config_seleccionada_id:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE configuracion_app
                SET icono_cerrar=%s, icono_cerrar_ruta_relativa=%s
                WHERE id_config=%s
            """, (ruta_absoluta, ruta_relativa, self.config_seleccionada_id))
            conexion.commit()
            conexion.close()


    def seleccionar_hero_imagen(self):
        ruta_absoluta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen principal", "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not ruta_absoluta:
            return

        # Convertir la ruta absoluta a relativa desde la carpeta 'public'
        ruta_base = os.path.abspath(os.path.join(os.getcwd(), "public"))
        ruta_relativa = os.path.relpath(ruta_absoluta, ruta_base).replace("\\", "/")
        ruta_relativa = f"/{ruta_relativa}"  # Añadir la barra inicial

        # Mostrar la ruta absoluta en el lineEdit
        self.lineEdit_hero_imagen.setText(ruta_absoluta)

        # Cargar la imagen en el QLabel
        if os.path.exists(ruta_absoluta):
            pixmap_hero = self.redondear_imagen(ruta_absoluta, self.label_imagen_central, circular=True)
            self.label_imagen_central.setPixmap(pixmap_hero)
            self.label_imagen_central.setText("")

        # Guardar en la base de datos
        if hasattr(self, 'config_seleccionada_id') and self.config_seleccionada_id:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE configuracion_app
                SET hero_imagen=%s, hero_imagen_ruta_relativa=%s
                WHERE id_config=%s
            """, (ruta_absoluta, ruta_relativa, self.config_seleccionada_id))
            conexion.commit()
            conexion.close()

    def redondear_imagen(self, ruta_imagen, label: QLabel = None, size: int = None, circular: bool = True):
        """
        Carga una imagen en un QLabel y la ajusta automáticamente.
        Funciona para imagen central o iconos, respetando bordes circulares si circular=True.

        Parámetros:
            ruta_imagen (str): Ruta de la imagen a cargar.
            label (QLabel, opcional): QLabel donde se mostrará la imagen.
            size (int, opcional): Tamaño en píxeles. Si se pasa, se usa en lugar del tamaño del label.
            circular (bool): Si True aplica borde circular, si False mantiene rectangular.
        
        Retorna:
            QPixmap: Imagen procesada.
        """
        if not ruta_imagen:
            if label:
                label.clear()
            return QPixmap()

        pixmap = QPixmap(ruta_imagen)
        if pixmap.isNull():
            if label:
                label.clear()
            return QPixmap()

        # Determinar tamaño
        if size is None and label:
            size = min(label.width(), label.height())
        elif size is None:
            size = 100  # Tamaño por defecto

        # Escalar la imagen para cubrir todo el espacio
        pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        if circular:
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
            resultado = mask
        else:
            resultado = pixmap

        if label:
            label.setPixmap(resultado)

        return resultado
