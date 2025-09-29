# app_sub_secciones.py
# -*- coding: utf-8 -*-
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import (
    QFileDialog, QTableWidgetItem, QApplication,
    QWidget, QMessageBox, QFrame, QVBoxLayout,
    QLabel, QHBoxLayout, QPushButton
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush, QPen, QColor, QPainterPath
from PyQt5.QtCore import Qt, QDate
from database import conectar_base_datos
from datetime import date, datetime
import os

# -------------------------
# HELPERS GENERALES
# -------------------------
def ruta_absoluta_desde_relativa(ruta_rel):
    """Convierte una ruta relativa en absoluta desde el directorio public/"""
    if not ruta_rel:
        return None

    # Normalizar para evitar que empiece con "/"
    ruta_rel = ruta_rel.lstrip("/")

    base_dir = os.path.abspath("public")
    ruta_abs = os.path.abspath(os.path.join(base_dir, ruta_rel))

    return ruta_abs

# -------------------------
# CLASE PRINCIPAL
# -------------------------
class VentanaSubSecciones(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlag(Qt.Window)
        self.resize(900, 700)

        self.parent_widget = parent
        self.id_subseccion_seleccionada = None
        self.edicion_subseccion = False
        self.region_zona_seleccionada = None
        self.regiones_zonas_data = {}
        self.secciones_data = {}

        # Cargar UI
        ruta_ui = os.path.join(os.path.dirname(__file__), "interfaz", "sub_secciones_app.ui")
        if not os.path.exists(ruta_ui):
            raise FileNotFoundError(f"No se encontró el archivo UI en: {ruta_ui}")
        uic.loadUi(ruta_ui, self)
        self.centrar_ventana()

        # Configurar fecha de desactivación
        self.dateEdit_fecha_desactivacion.setSpecialValueText("")
        self.dateEdit_fecha_desactivacion.setDate(QDate.currentDate())

        # Layouts para cards
        self.layout_activos = QtWidgets.QGridLayout(self.contenedor_elementos_activos)
        self.layout_inactivos = QtWidgets.QGridLayout(self.contenedor_elementos_inactivos)
        self.layout_activos.setSpacing(10)
        self.layout_inactivos.setSpacing(10)

        # Cargar datos iniciales
        self.cargar_regiones_zonas()
        self.cargar_secciones_en_combo()

        # Conexiones
        self.comboBox_seccion.setEnabled(False)
        self.comboBox_region_zona.currentIndexChanged.connect(self.on_region_zona_changed)
        self.comboBox_seccion.currentIndexChanged.connect(self.on_combo_seccion_changed)
        self.comboBox_seccion1.currentIndexChanged.connect(self.on_combo_seccion_changed)
        
        self.btnAgregar.clicked.connect(self.agregar_sub_seccion)
        self.btnModificar.clicked.connect(self.modificar_sub_seccion)
        self.btnEliminar.clicked.connect(self.eliminar_sub_seccion)
        self.btnDesactivar.clicked.connect(self.desactivar_sub_seccion)
        self.btnLimpiarFormulario.clicked.connect(self.limpiar_formulario)
        self.btnCerrar.clicked.connect(self.close)

        # Selección de imágenes
        self.btnBuscarImagen.clicked.connect(
            lambda: self.seleccionar_archivo(self.label_imagen, self.lineEdit_imagen, 200, 150, "public/assets/imagenes")
        )
        
        # Selección de fotos
        self.btnBuscarFoto1.clicked.connect(lambda: self.seleccionar_archivo(self.label_foto_1, self.lineEdit_foto_1, 200, 150, "public/assets/imagenes"))
        self.btnBuscarFoto2.clicked.connect(lambda: self.seleccionar_archivo(self.label_foto_2, self.lineEdit_foto_2, 200, 150, "public/assets/imagenes"))
        self.btnBuscarFoto3.clicked.connect(lambda: self.seleccionar_archivo(self.label_foto_3, self.lineEdit_foto_3, 200, 150, "public/assets/imagenes"))
        self.btnBuscarFoto4.clicked.connect(lambda: self.seleccionar_archivo(self.label_foto_4, self.lineEdit_foto_4, 200, 150, "public/assets/imagenes"))

    # -------------------------
    # EVENTOS DE VENTANA
    # -------------------------
    def closeEvent(self, event):
        """Maneja el cierre de la ventana"""
        if self.parent():
            self.parent().mostrar_menu_lateral()
        super().closeEvent(event)

    def centrar_ventana(self):
        """Centra la ventana en la pantalla"""
        pantalla = QApplication.primaryScreen().availableGeometry()
        ventana = self.frameGeometry()
        ventana.moveCenter(pantalla.center())
        self.move(ventana.topLeft())

    # -------------------------
    # MANEJO DE REGIONES/ZONAS
    # -------------------------
    def cargar_regiones_zonas(self):
        """Carga las regiones/zonas habilitadas en el comboBox"""
        conexion = conectar_base_datos()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("""
            SELECT id_region_zona, nombre_region_zona, imagen_region_zona_ruta_relativa 
            FROM regiones_zonas 
            WHERE habilitar=1 
            ORDER BY orden ASC
        """)
        regiones_zonas = cursor.fetchall()
        conexion.close()
        
        self.comboBox_region_zona.clear()
        self.comboBox_region_zona.addItem("— Seleccionar región/zona —", None)
        
        self.regiones_zonas_data = {}
        
        for rz in regiones_zonas:
            self.comboBox_region_zona.addItem(rz["nombre_region_zona"], rz["id_region_zona"])
            self.regiones_zonas_data[rz["id_region_zona"]] = {
                'imagen': rz["imagen_region_zona_ruta_relativa"],
                'nombre': rz["nombre_region_zona"]
            }

    def on_region_zona_changed(self, index):
        """Maneja el cambio de selección en regiones/zonas"""
        if index == 0:
            self.label_imagen_region_zona.clear()
            self.region_zona_seleccionada = None
            return
            
        id_region_zona = self.comboBox_region_zona.currentData()
        
        if not id_region_zona:
            return
            
        self.region_zona_seleccionada = id_region_zona
        
        if id_region_zona in self.regiones_zonas_data:
            imagen_ruta_rel = self.regiones_zonas_data[id_region_zona]['imagen']
            
            if imagen_ruta_rel:
                ruta_abs = ruta_absoluta_desde_relativa(imagen_ruta_rel)
                if ruta_abs and os.path.exists(ruta_abs):
                    pixmap = QPixmap(ruta_abs).scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.label_imagen_region_zona.setPixmap(pixmap)
                    self.label_imagen_region_zona.setToolTip(f"Región/Zona: {self.regiones_zonas_data[id_region_zona]['nombre']}")
                else:
                    self.label_imagen_region_zona.clear()
                    self.label_imagen_region_zona.setText("Imagen no encontrada")
            else:
                self.label_imagen_region_zona.clear()
                self.label_imagen_region_zona.setText("Sin imagen")
        self.comboBox_seccion.setEnabled(True)
        self.cargar_sub_secciones()

    # -------------------------
    # MANEJO DE SECCIONES
    # -------------------------
    def cargar_secciones_en_combo(self):
        """Carga las secciones en los combos y prepara datos de iconos"""
        conexion = conectar_base_datos()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT id_seccion, nombre_seccion, icono_seccion FROM secciones WHERE habilitar=1 ORDER BY orden ASC")
        secciones = cursor.fetchall()
        conexion.close()
        
        self.comboBox_seccion.clear()
        self.comboBox_seccion.addItem("— Seleccionar sección —", None)
        
        self.secciones_data = {}
        
        for s in secciones:
            self.comboBox_seccion.addItem(s["nombre_seccion"], s["id_seccion"])
            self.secciones_data[s["id_seccion"]] = {
                'icono': s["icono_seccion"],
                'nombre': s["nombre_seccion"]
            }
        
        self.comboBox_seccion1.clear()
        self.comboBox_seccion1.addItem("— Seleccionar sección —", None)
        for s in secciones:
            self.comboBox_seccion1.addItem(s["nombre_seccion"], s["id_seccion"])

    def on_combo_seccion_changed(self, index):
        """Maneja el cambio de selección en secciones"""
        if self.edicion_subseccion:
            return
            
        sender = self.sender()
        id_seccion = sender.currentData()
        
        if id_seccion and id_seccion in self.secciones_data:
            icono_ruta = self.secciones_data[id_seccion]['icono']
            
            if icono_ruta:
                ruta_abs = ruta_absoluta_desde_relativa(icono_ruta)
                
                if ruta_abs and os.path.exists(ruta_abs):
                    pixmap = QPixmap(ruta_abs).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.label_icono.setPixmap(pixmap)
                    self.label_icono.setToolTip(f"Icono de: {self.secciones_data[id_seccion]['nombre']}")
                else:
                    self.label_icono.clear()
                    self.label_icono.setText("Icono no disponible")
                
                self.lineEdit_icono.setText(icono_ruta)
            else:
                self.label_icono.clear()
                self.lineEdit_icono.clear()
                self.label_icono.setText("Sin icono")
        
        if sender == self.comboBox_seccion:
            self.cargar_sub_secciones()
        elif sender == self.comboBox_seccion1:
            self.cargar_sub_secciones_inactivas()

    # -------------------------
    # SELECCIÓN DE ARCHIVOS
    # -------------------------
    def seleccionar_archivo(self, label_obj, lineedit_obj, ancho, alto, carpeta_destino):
        """Abre diálogo para seleccionar archivo y lo carga en la UI"""
        archivo, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo", "", "Imágenes (*.png *.jpg *.jpeg *.bmp)"
        )
        if archivo:
            ruta_absoluta = os.path.abspath(archivo)

            try:
                ruta_relativa = os.path.relpath(ruta_absoluta, os.path.join(os.getcwd(), "public")).replace("\\", "/")
                ruta_relativa = "/" + ruta_relativa
            except ValueError:
                ruta_relativa = os.path.basename(ruta_absoluta)

            pixmap = QPixmap(ruta_absoluta).scaled(ancho, alto, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label_obj.setPixmap(pixmap)

            label_obj.setToolTip(f"ABS:{ruta_absoluta}|REL:{ruta_relativa}")
            lineedit_obj.setText(ruta_relativa)
            label_obj.ruta_absoluta = ruta_absoluta

    # -------------------------
    # CARGA DE SUBSECCIONES
    # -------------------------
    def cargar_sub_secciones(self):
        """Carga las subsecciones activas filtradas por región/zona y sección"""
        for i in reversed(range(self.layout_activos.count())):
            item = self.layout_activos.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)

        id_seccion = self.comboBox_seccion.currentData()
        id_region_zona = self.region_zona_seleccionada

        if not id_seccion:
            return

        conexion = conectar_base_datos()
        cursor = conexion.cursor(dictionary=True)
        hoy = date.today().strftime("%Y-%m-%d")
        
        if id_region_zona:
            cursor.execute("""
                SELECT ss.* 
                FROM sub_secciones ss
                WHERE ss.id_seccion = %s 
                AND ss.id_region_zona = %s
                AND ss.habilitar = 1
                AND (ss.fecha_desactivacion IS NULL OR ss.fecha_desactivacion > %s)
                ORDER BY ss.orden ASC
            """, (id_seccion, id_region_zona, hoy))
        else:
            cursor.execute("""
                SELECT ss.* 
                FROM sub_secciones ss
                WHERE ss.id_seccion = %s 
                AND ss.habilitar = 1
                AND (ss.fecha_desactivacion IS NULL OR ss.fecha_desactivacion > %s)
                ORDER BY ss.orden ASC
            """, (id_seccion, hoy))
            
        filas = cursor.fetchall()
        conexion.close()

        self.subsecciones = filas

        row, col = 0, 0
        for fila in filas:
            fila["imagen_final"] = ruta_absoluta_desde_relativa(fila.get("imagen_ruta_relativa")) or fila.get("imagen")
            fila["icono_final"] = ruta_absoluta_desde_relativa(fila.get("icono_ruta_relativa")) or fila.get("icono")

            for idx in range(1, 5):
                fila[f"foto{idx}_final"] = (
                    ruta_absoluta_desde_relativa(fila.get(f"foto{idx}_ruta_relativa"))
                    or fila.get(f"foto{idx}_ruta_absoluta")
                )

            card = self.crear_card(fila)
            card.subseccion_id = fila.get("id_sub_seccion")
            card.mousePressEvent = lambda event, c=card: self.on_card_clicked(c)

            self.layout_activos.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1

    def cargar_sub_secciones_inactivas(self):
        """Carga las subsecciones inactivas filtradas por región/zona y sección"""
        for i in reversed(range(self.layout_inactivos.count())):
            item = self.layout_inactivos.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)

        id_seccion = self.comboBox_seccion1.currentData()
        id_region_zona = self.region_zona_seleccionada

        if not id_seccion:
            return

        conexion = conectar_base_datos()
        cursor = conexion.cursor(dictionary=True)
        
        if id_region_zona:
            cursor.execute("""
                SELECT ss.* 
                FROM sub_secciones ss
                WHERE ss.id_seccion = %s
                AND ss.id_region_zona = %s
                AND (ss.habilitar = 0 OR (ss.fecha_desactivacion IS NOT NULL AND ss.fecha_desactivacion <= CURDATE()))
                ORDER BY ss.orden ASC
            """, (id_seccion, id_region_zona))
        else:
            cursor.execute("""
                SELECT ss.* 
                FROM sub_secciones ss
                WHERE ss.id_seccion = %s
                AND (ss.habilitar = 0 OR (ss.fecha_desactivacion IS NOT NULL AND ss.fecha_desactivacion <= CURDATE()))
                ORDER BY ss.orden ASC
            """, (id_seccion,))
            
        filas = cursor.fetchall()
        conexion.close()

        self.subsecciones_inactivas = filas

        row, col = 0, 0
        for fila in filas:
            fila["imagen_final"] = ruta_absoluta_desde_relativa(fila.get("imagen_ruta_relativa")) or fila.get("imagen")
            fila["icono_final"] = ruta_absoluta_desde_relativa(fila.get("icono_ruta_relativa")) or fila.get("icono")

            for idx in range(1, 5):
                fila[f"foto{idx}_final"] = (
                    ruta_absoluta_desde_relativa(fila.get(f"foto{idx}_ruta_relativa"))
                    or fila.get(f"foto{idx}_ruta_absoluta")
                )

            card = self.crear_card(fila, inactivo=True)
            card.mousePressEvent = lambda event, f=fila: self.on_card_clicked_inactiva(f)

            self.layout_inactivos.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1

    # -------------------------
    # CREACIÓN DE CARDS
    # -------------------------
    def crear_card(self, elemento, inactivo=False):
        """Crea una tarjeta visual para una subsección"""
        card = QFrame()
        card.setFrameShape(QFrame.Box)
        card.setLineWidth(1)
        card.setFixedSize(220, 300)
        layout = QVBoxLayout(card)

        # Icono
        icono_label = QLabel()
        icono_label.setFixedSize(48, 48)
        icono_label.setAlignment(Qt.AlignCenter)
        ruta_icono = elemento.get("icono_final")
        self.cargar_imagen_icono(ruta=ruta_icono, label_widget=icono_label, size=(48, 48))
        layout.addWidget(icono_label)

        # Nombre
        nombre_label = QLabel(elemento.get("nombre_sub_seccion", ""))
        nombre_label.setAlignment(Qt.AlignCenter)
        nombre_label.setWordWrap(True)
        layout.addWidget(nombre_label)

        # Imagen principal
        imagen_label = QLabel()
        imagen_label.setFixedSize(180, 120)
        imagen_label.setAlignment(Qt.AlignCenter)
        imagen_label.setScaledContents(True)
        ruta_img = elemento.get("imagen_final")
        self.cargar_imagen_icono(ruta=ruta_img, label_widget=imagen_label, size=(180, 120))
        layout.addWidget(imagen_label)

        # Estado
        estado_label = QLabel("INACTIVO" if inactivo else "ACTIVO")
        estado_label.setAlignment(Qt.AlignCenter)
        estado_label.setStyleSheet("color: red;" if inactivo else "color: green;")
        layout.addWidget(estado_label)

        card.subseccion_id = elemento.get("id_sub_seccion")
        return card

    def cargar_imagen_icono(self, ruta, label_widget, size=None, fallback_text="Sin imagen"):
        """Carga una imagen en un QLabel con manejo de errores"""
        if not ruta:
            label_widget.clear()
            label_widget.setText(fallback_text)
            return

        ruta_a_usar = ruta
        if not os.path.exists(ruta_a_usar):
            ruta_abs = ruta_absoluta_desde_relativa(ruta_a_usar)
            if ruta_abs and os.path.exists(ruta_abs):
                ruta_a_usar = ruta_abs
            else:
                label_widget.clear()
                label_widget.setText(fallback_text)
                return

        pixmap = QPixmap(ruta_a_usar)
        if size:
            pixmap = pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label_widget.setPixmap(pixmap)

    # -------------------------
    # MANEJO DE CLICS EN CARDS
    # -------------------------
    def on_card_clicked(self, card_widget):
        """Maneja el clic en una card activa"""
        subseccion_id = getattr(card_widget, "subseccion_id", None)
        if not subseccion_id:
            return

        subseccion = next((s for s in self.subsecciones if s['id_sub_seccion'] == subseccion_id), None)
        if not subseccion:
            return

        fila = {
            "id_sub_seccion": subseccion['id_sub_seccion'],
            "nombre_sub_seccion": subseccion.get('nombre_sub_seccion', ''),
            "orden": subseccion.get('orden', ''),
            "destacado": subseccion.get('destacado',''),
            "id_seccion": subseccion.get('id_seccion'),
            "id_region_zona": subseccion.get('id_region_zona'),  # Nuevo campo
            "domicilio": subseccion.get('domicilio', ''),
            "latitud": subseccion.get('latitud'),
            "longitud": subseccion.get('longitud'),
            "distancia": subseccion.get('distancia', ''),
            "numero_telefono": subseccion.get('numero_telefono', ''),
            "imagen_abs": subseccion.get('imagen'),
            "imagen_rel": subseccion.get('imagen_ruta_relativa'),
            "icono_abs": subseccion.get('icono'),
            "icono_rel": subseccion.get('icono_ruta_relativa'),
            "foto1_abs": subseccion.get('foto1_ruta_absoluta'),
            "foto1_rel": subseccion.get('foto1_ruta_relativa'),
            "foto2_abs": subseccion.get('foto2_ruta_absoluta'),
            "foto2_rel": subseccion.get('foto2_ruta_relativa'),
            "foto3_abs": subseccion.get('foto3_ruta_absoluta'),
            "foto3_rel": subseccion.get('foto3_ruta_relativa'),
            "foto4_abs": subseccion.get('foto4_ruta_absoluta'),
            "foto4_rel": subseccion.get('foto4_ruta_relativa'),
            "itinerario_maps": subseccion.get('itinerario_maps', '')
        }

        self.cargar_sub_seccion_en_formulario(fila)

    def on_card_clicked_inactiva(self, fila):
        """Maneja el clic en una card inactiva (reactivación)"""
        if not fila:
            return

        self.id_subseccion_seleccionada = fila.get("id_sub_seccion") or fila.get("id")
        nombre = fila.get("nombre_sub_seccion", "esta sub-sección")

        respuesta = QMessageBox.question(
            self,
            "Reactivar sub-sección",
            f"¿Desea reactivar '{nombre}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if respuesta != QMessageBox.Yes:
            return

        try:
            conn = conectar_base_datos()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sub_secciones
                SET habilitar = 1,
                    fecha_desactivacion = NULL
                WHERE id_sub_seccion = %s
            """, (self.id_subseccion_seleccionada,))
            conn.commit()
            cursor.close()
            conn.close()

            QMessageBox.information(self, "Éxito", "Sub-sección reactivada correctamente")
            self.cargar_sub_secciones()
            self.cargar_sub_secciones_inactivas()
            self.limpiar_formulario()
            self.id_subseccion_seleccionada = None

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo reactivar: {e}")

    # -------------------------
    # FORMULARIO
    # -------------------------
    def cargar_sub_seccion_en_formulario(self, fila):
        """Carga los datos de una subsección en el formulario"""
        if not fila:
            return

        self.id_subseccion_seleccionada = fila.get("id_sub_seccion") or fila.get("id")

        # Campos básicos
        self.lineEdit_nombre_subSeccion.setText(fila.get("nombre_sub_seccion", "") or "")
        self.lineEdit_domicilio.setText(fila.get("domicilio", "") or "")
        self.lineEdit_latitud.setText("" if fila.get("latitud") is None else str(fila["latitud"]))
        self.lineEdit_longitud.setText("" if fila.get("longitud") is None else str(fila["longitud"]))
        self.lineEdit_distancia.setText(fila.get("distancia", "") or "")
        self.lineEdit_numero_telefono.setText(fila.get("numero_telefono", "") or "")
        self.lineEdit_itinerario.setText(fila.get("itinerario_maps", "") or "")

        # Rutas relativas
        self.lineEdit_imagen.setText(fila.get("imagen_rel", "") or "")
        self.lineEdit_icono.setText(fila.get("icono_rel", "") or "")
        self.lineEdit_foto_1.setText(fila.get("foto1_rel", "") or "")
        self.lineEdit_foto_2.setText(fila.get("foto2_rel", "") or "")
        self.lineEdit_foto_3.setText(fila.get("foto3_rel", "") or "")
        self.lineEdit_foto_4.setText(fila.get("foto4_rel", "") or "")

        # Campos numéricos y booleanos
        try:
            self.spinBox_orden.setValue(int(fila.get("orden", 0)))
        except Exception:
            self.spinBox_orden.setValue(0)
        
        try:
            self.checkBox_destacado.setChecked(bool(int(fila.get("destacado", 0))))
        except Exception:
            self.checkBox_destacado.setChecked(False)

        # Cargar imágenes
        self.cargar_imagen_formulario(self.label_imagen, fila.get("imagen_abs"), fila.get("imagen_rel"), (200,150))
        self.cargar_imagen_formulario(self.label_icono, fila.get("icono_abs"), fila.get("icono_rel"), (48,48))
        self.cargar_imagen_formulario(self.label_foto_1, fila.get("foto1_abs"), fila.get("foto1_rel"), (200,150))
        self.cargar_imagen_formulario(self.label_foto_2, fila.get("foto2_abs"), fila.get("foto2_rel"), (200,150))
        self.cargar_imagen_formulario(self.label_foto_3, fila.get("foto3_abs"), fila.get("foto3_rel"), (200,150))
        self.cargar_imagen_formulario(self.label_foto_4, fila.get("foto4_abs"), fila.get("foto4_rel"), (200,150))

        # ComboBox de sección
        id_seccion = fila.get("id_seccion")
        index_combo = self.comboBox_seccion.findData(id_seccion)
        if index_combo >= 0:
            self.comboBox_seccion.setCurrentIndex(index_combo)

        # ComboBox de región/zona
        id_region_zona = fila.get("id_region_zona")
        if id_region_zona:
            index_region = self.comboBox_region_zona.findData(id_region_zona)
            if index_region >= 0:
                self.comboBox_region_zona.setCurrentIndex(index_region)

        # Fecha de desactivación
        fecha_desac = fila.get("fecha_desactivacion")
        if fecha_desac and isinstance(fecha_desac, str):
            try:
                year, month, day = map(int, fecha_desac.split("-"))
                qdate = QDate(year, month, day)
                if qdate.isValid():
                    self.dateEdit_fecha_desactivacion.setDate(qdate)
                else:
                    self.dateEdit_fecha_desactivacion.setDate(QDate.currentDate())
            except Exception:
                self.dateEdit_fecha_desactivacion.setDate(QDate.currentDate())
        else:
            self.dateEdit_fecha_desactivacion.setDate(QDate.currentDate())

        # Estado de botones
        self.btnAgregar.setEnabled(False)
        self.btnModificar.setEnabled(True)
        self.btnEliminar.setEnabled(True)
        self.btnDesactivar.setEnabled(True)

        self.edicion_subseccion = True

    def cargar_imagen_formulario(self, label_widget, ruta_abs, ruta_rel, size):
        """Carga una imagen en el formulario con tooltip"""
        tooltip = f"ABS:{ruta_abs or ''} | REL:{ruta_rel or ''}"
        label_widget.setToolTip(tooltip)

        ruta_a_usar = ""
        if ruta_abs and os.path.exists(ruta_abs):
            ruta_a_usar = ruta_abs
        elif ruta_rel:
            ruta_tmp = ruta_absoluta_desde_relativa(ruta_rel)
            if ruta_tmp and os.path.exists(ruta_tmp):
                ruta_a_usar = ruta_tmp

        self.cargar_imagen_icono(ruta=ruta_a_usar, label_widget=label_widget, size=size)

    def limpiar_formulario(self):
        """Limpia todos los campos del formulario"""
        self.id_subseccion_seleccionada = None
        self.edicion_subseccion = False

        # Limpiar campos de texto
        self.lineEdit_nombre_subSeccion.clear()
        self.lineEdit_domicilio.clear()
        self.lineEdit_latitud.clear()
        self.lineEdit_longitud.clear()
        self.lineEdit_distancia.clear()
        self.lineEdit_numero_telefono.clear()
        self.lineEdit_imagen.clear()
        self.lineEdit_icono.clear()
        self.lineEdit_foto_1.clear()
        self.lineEdit_foto_2.clear()
        self.lineEdit_foto_3.clear()
        self.lineEdit_foto_4.clear()
        self.lineEdit_itinerario.clear()

        # Limpiar imágenes
        for label in [
            self.label_imagen, self.label_icono,
            self.label_foto_1, self.label_foto_2,
            self.label_foto_3, self.label_foto_4
        ]:
            label.clear()
            label.setToolTip("")

        # Resetear combos
        self.comboBox_seccion.setEnabled(False)
        self.comboBox_seccion.setCurrentIndex(0)
        self.comboBox_region_zona.setCurrentIndex(0)
        self.dateEdit_fecha_desactivacion.setDate(QDate.currentDate())
        self.spinBox_orden.setValue(0)
        self.checkBox_destacado.setChecked(False)

        # Estado de botones
        self.btnAgregar.setEnabled(True)
        self.btnModificar.setEnabled(False)
        self.btnEliminar.setEnabled(False)
        self.btnDesactivar.setEnabled(False)
    
    # -------------------------
    # OPERACIONES CRUD (ADAPTADAS)
    # -------------------------
    def agregar_sub_seccion(self):
        """Agrega una nueva subsección incluyendo región/zona"""
        # Validaciones básicas
        nombre = self.lineEdit_nombre_subSeccion.text().strip()
        id_seccion = self.comboBox_seccion.currentData()
        id_region_zona = self.region_zona_seleccionada

        if not nombre or not id_seccion:
            QMessageBox.warning(self, "Error", "Debe completar nombre y sección")
            return

        if not id_region_zona:
            QMessageBox.warning(self, "Error", "Debe seleccionar una región/zona")
            return

        # Campos básicos
        domicilio = self.lineEdit_domicilio.text().strip()
        distancia = self.lineEdit_distancia.text().strip()
        telefono = self.lineEdit_numero_telefono.text().strip()
        itinerario = self.lineEdit_itinerario.text().strip()
        habilitar = 1
        orden = self.spinBox_orden.value()  # CORREGIDO: usar value() en lugar de text()
        destacado = 1 if self.checkBox_destacado.isChecked() else 0

        # Fecha de desactivación
        fecha_qdate = self.dateEdit_fecha_desactivacion.date()
        fecha = fecha_qdate.toPyDate() if fecha_qdate.isValid() else None

        # Validar coordenadas
        try:
            latitud = float(self.lineEdit_latitud.text().replace(",", ".").strip())
            if not (-90 <= latitud <= 90):
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Error", "Latitud inválida. Debe ser un número decimal entre -90 y 90")
            return

        try:
            longitud = float(self.lineEdit_longitud.text().replace(",", ".").strip())
            if not (-180 <= longitud <= 180):
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Error", "Longitud inválida. Debe ser un número decimal entre -180 y 180")
            return

        # Helper para procesar rutas
        def procesar_ruta(lineedit, base_dir):
            ruta_rel = lineedit.text().strip() or None
            if ruta_rel:
                ruta_abs = os.path.abspath(os.path.join(base_dir, ruta_rel))
                ruta_rel = ruta_rel.replace("\\", "/")
            else:
                ruta_abs = None
            return ruta_abs, ruta_rel

        base_imagenes = os.path.abspath("public/assets/imagenes")
        base_iconos = os.path.abspath("public/assets/iconos")

        # Rutas de imagen, icono y fotos
        imagen_abs, imagen_rel = procesar_ruta(self.lineEdit_imagen, base_imagenes)
        icono_abs, icono_rel = procesar_ruta(self.lineEdit_icono, base_iconos)
        foto1_abs, foto1_rel = procesar_ruta(self.lineEdit_foto_1, base_imagenes)
        foto2_abs, foto2_rel = procesar_ruta(self.lineEdit_foto_2, base_imagenes)
        foto3_abs, foto3_rel = procesar_ruta(self.lineEdit_foto_3, base_imagenes)
        foto4_abs, foto4_rel = procesar_ruta(self.lineEdit_foto_4, base_imagenes)

        # Insertar en DB
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO sub_secciones 
                (id_seccion, id_region_zona, nombre_sub_seccion, domicilio, latitud, longitud, 
                distancia, numero_telefono, imagen, imagen_ruta_relativa, icono, icono_ruta_relativa, 
                itinerario_maps, habilitar, fecha_desactivacion, orden, destacado,
                foto1_ruta_absoluta, foto1_ruta_relativa, foto2_ruta_absoluta, foto2_ruta_relativa,
                foto3_ruta_absoluta, foto3_ruta_relativa, foto4_ruta_absoluta, foto4_ruta_relativa)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                id_seccion, id_region_zona, nombre, domicilio, latitud, longitud, 
                distancia, telefono, imagen_abs, imagen_rel, icono_abs, icono_rel, 
                itinerario, habilitar, fecha, orden, destacado,
                foto1_abs, foto1_rel, foto2_abs, foto2_rel, 
                foto3_abs, foto3_rel, foto4_abs, foto4_rel
            ))
            conexion.commit()
            conexion.close()

            QMessageBox.information(self, "Éxito", "Subsección agregada correctamente")
            self.limpiar_formulario()
            self.cargar_sub_secciones()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo agregar la subsección: {str(e)}")

    def modificar_sub_seccion(self):
        """Modifica una subsección existente incluyendo región/zona"""
        if not self.id_subseccion_seleccionada:
            QMessageBox.warning(self, "Error", "Seleccione una subsección para modificar")
            return

        # Campos básicos
        nombre = self.lineEdit_nombre_subSeccion.text().strip()
        domicilio = self.lineEdit_domicilio.text().strip()
        distancia = self.lineEdit_distancia.text().strip()
        telefono = self.lineEdit_numero_telefono.text().strip()
        itinerario = self.lineEdit_itinerario.text().strip()
        habilitar = 1
        orden = self.spinBox_orden.value()  # CORREGIDO: usar value()
        destacado = 1 if self.checkBox_destacado.isChecked() else 0

        id_seccion = self.comboBox_seccion.currentData()
        id_region_zona = self.region_zona_seleccionada

        if not nombre or not id_seccion:
            QMessageBox.warning(self, "Error", "Debe completar nombre y sección")
            return

        if not id_region_zona:
            QMessageBox.warning(self, "Error", "Debe seleccionar una región/zona")
            return

        # Fecha de desactivación
        fecha_qdate = self.dateEdit_fecha_desactivacion.date()
        fecha = fecha_qdate.toPyDate() if fecha_qdate.isValid() else None

        # Validar coordenadas
        try:
            latitud = float(self.lineEdit_latitud.text().replace(",", ".").strip())
            if not (-90 <= latitud <= 90):
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Error", "Latitud inválida. Debe ser un número decimal entre -90 y 90")
            return

        try:
            longitud = float(self.lineEdit_longitud.text().replace(",", ".").strip())
            if not (-180 <= longitud <= 180):
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Error", "Longitud inválida. Debe ser un número decimal entre -180 y 180")
            return

        # Helper para procesar rutas
        def procesar_ruta(lineedit, base_dir):
            ruta_rel = lineedit.text().strip() or None
            if ruta_rel:
                ruta_abs = os.path.abspath(os.path.join(base_dir, ruta_rel))
                ruta_rel = ruta_rel.replace("\\", "/")
            else:
                ruta_abs = None
            return ruta_abs, ruta_rel

        base_imagenes = os.path.abspath("public/assets/imagenes")
        base_iconos = os.path.abspath("public/assets/iconos")

        # Rutas de imagen, icono y fotos
        imagen_abs, imagen_rel = procesar_ruta(self.lineEdit_imagen, base_imagenes)
        icono_abs, icono_rel = procesar_ruta(self.lineEdit_icono, base_iconos)
        foto1_abs, foto1_rel = procesar_ruta(self.lineEdit_foto_1, base_imagenes)
        foto2_abs, foto2_rel = procesar_ruta(self.lineEdit_foto_2, base_imagenes)
        foto3_abs, foto3_rel = procesar_ruta(self.lineEdit_foto_3, base_imagenes)
        foto4_abs, foto4_rel = procesar_ruta(self.lineEdit_foto_4, base_imagenes)

        # Actualizar en DB
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE sub_secciones
                SET id_seccion = %s,
                    id_region_zona = %s,
                    nombre_sub_seccion = %s,
                    domicilio = %s,                
                    latitud = %s,
                    longitud = %s,
                    distancia = %s,
                    numero_telefono = %s,
                    imagen = %s,
                    imagen_ruta_relativa = %s,
                    icono = %s,
                    icono_ruta_relativa = %s,
                    itinerario_maps = %s,
                    habilitar = %s,
                    fecha_desactivacion = %s,
                    orden = %s,
                    destacado = %s,
                    foto1_ruta_absoluta = %s, 
                    foto1_ruta_relativa = %s,
                    foto2_ruta_absoluta = %s, 
                    foto2_ruta_relativa = %s,
                    foto3_ruta_absoluta = %s, 
                    foto3_ruta_relativa = %s,
                    foto4_ruta_absoluta = %s, 
                    foto4_ruta_relativa = %s
                WHERE id_sub_seccion = %s
            """, (
                id_seccion, id_region_zona, nombre, domicilio, latitud, longitud, 
                distancia, telefono, imagen_abs, imagen_rel, icono_abs, icono_rel, 
                itinerario, habilitar, fecha, orden, destacado,
                foto1_abs, foto1_rel, foto2_abs, foto2_rel, 
                foto3_abs, foto3_rel, foto4_abs, foto4_rel,
                self.id_subseccion_seleccionada
            ))
            conexion.commit()
            conexion.close()

            QMessageBox.information(self, "Éxito", "Subsección modificada correctamente")
            self.limpiar_formulario()
            self.cargar_sub_secciones()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo modificar la subsección: {str(e)}")

    def eliminar_sub_seccion(self):
        """Elimina una subsección"""
        if not self.id_subseccion_seleccionada:
            QMessageBox.warning(self, "Error", "Seleccione una subsección para eliminar")
            return
        
        resp = QMessageBox.question(
            self, 
            "Confirmar eliminación", 
            "¿Está seguro de que desea eliminar esta subsección?\nEsta acción no se puede deshacer.", 
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if resp == QMessageBox.Yes:
            try:
                conexion = conectar_base_datos()
                cursor = conexion.cursor()
                cursor.execute("DELETE FROM sub_secciones WHERE id_sub_seccion = %s", (self.id_subseccion_seleccionada,))
                conexion.commit()
                conexion.close()
                
                QMessageBox.information(self, "Éxito", "Subsección eliminada correctamente")
                self.limpiar_formulario()
                self.cargar_sub_secciones()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar la subsección: {str(e)}")

    def desactivar_sub_seccion(self):
        """Desactiva una subsección (la mueve a inactivas)"""
        if not self.id_subseccion_seleccionada:
            QMessageBox.warning(self, "Error", "Seleccione una subsección para desactivar")
            return
        
        nombre = self.lineEdit_nombre_subSeccion.text().strip() or "esta subsección"
        
        resp = QMessageBox.question(
            self, 
            "Confirmar desactivación", 
            f"¿Desea desactivar '{nombre}'?\nLa subsección se moverá a la lista de inactivas.", 
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if resp == QMessageBox.Yes:
            try:
                hoy = date.today().strftime("%Y-%m-%d")
                conexion = conectar_base_datos()
                cursor = conexion.cursor()
                cursor.execute("""
                    UPDATE sub_secciones
                    SET habilitar = 0, 
                        fecha_desactivacion = %s
                    WHERE id_sub_seccion = %s
                """, (hoy, self.id_subseccion_seleccionada))
                conexion.commit()
                conexion.close()
                
                QMessageBox.information(self, "Éxito", "Subsección desactivada correctamente")
                self.limpiar_formulario()
                self.cargar_sub_secciones()
                self.cargar_sub_secciones_inactivas()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo desactivar la subsección: {str(e)}")