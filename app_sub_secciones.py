# app_sub_secciones.py
# -*- coding: utf-8 -*-
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import (
    QFileDialog, QTableWidgetItem, QApplication,
    QWidget, QMessageBox, QFrame, QVBoxLayout,
    QLabel, QHBoxLayout, QPushButton
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush, QPen, QColor, QPainterPath
from PyQt5.QtCore import Qt, QDate, QRectF
from database_hosting import conectar_hosting as conectar_base_datos
from datetime import date, datetime
import os
import shutil
import hashlib
import requests

# -------------------------
# MÉTODOS DE BÚSQUEDA HÍBRIDA (COPIADOS DE app_secciones.py)
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
                url_completa = f"{base_url}{ruta_limpia}"
                return url_completa
    except Exception as e:
        # print(f"Error obteniendo URL remota: {e}")
        pass
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
    Busca imágenes en REMOTO → LOCAL (igual que app_secciones.py)
    """
    # 1. PRIMERO: Buscar en REMOTO usando ruta relativa
    if ruta_relativa_db:
        url_remota = obtener_url_remota(ruta_relativa_db)
        if url_remota and verificar_url_remota(url_remota):
            # print(f"✅ [SUB_SECCIONES] Encontrado en REMOTO: {url_remota}")
            return url_remota
    
    # 2. SEGUNDO: Buscar en LOCAL con ruta absoluta
    if ruta_absoluta_db and os.path.exists(ruta_absoluta_db):
        # print(f"✅ [SUB_SECCIONES] Encontrado en LOCAL: {ruta_absoluta_db}")
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
                # print(f"✅ [SUB_SECCIONES] Encontrado en PROYECTO: {ruta}")
                return ruta
    
    # print(f"❌ [SUB_SECCIONES] No encontrado: {ruta_relativa_db}")
    return ""

def cargar_imagen_desde_ruta(ruta_imagen: str, size: tuple = None):
    """
    Carga imagen desde URL remota o archivo local
    """
    if not ruta_imagen:
        return None

    try:
        # ✅ MANEJAR URL REMOTA
        if _is_url(ruta_imagen):
            response = requests.get(ruta_imagen, timeout=10)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                if not pixmap.isNull():
                    if size:
                        pixmap = pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    # print(f"✅ [SUB_SECCIONES] Imagen remota cargada: {ruta_imagen}")
                    return pixmap
            return None
        
        # ✅ MANEJAR ARCHIVO LOCAL
        elif os.path.exists(ruta_imagen):
            pixmap = QPixmap(ruta_imagen)
            if not pixmap.isNull():
                if size:
                    pixmap = pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
                # print(f"✅ [SUB_SECCIONES] Imagen local cargada: {ruta_imagen}")
                return pixmap
        
        return None
        
    except Exception as e:
        # print(f"❌ [SUB_SECCIONES] Error cargando imagen: {e}")
        return None

def ruta_absoluta_desde_relativa(relativa):
    """
    Convierte '/assets/...png' a la ruta absoluta correcta.
    """
    if not relativa:
        return ""
    # Subimos dos niveles desde src/backend a la raíz del proyecto
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  
    base_assets = os.path.join(base_dir, "turismo-frontend", "public")
    return os.path.join(base_assets, relativa.lstrip("/"))

def convertir_ruta_produccion(ruta_absoluta):
    """Convierte rutas absolutas a rutas relativas - VERSIÓN FINAL"""
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
# CLASE PRINCIPAL CON SISTEMA HÍBRIDO
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
        self.subsecciones = []
        self.subsecciones_inactivas = []

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

        # Conexiones de búsqueda de archivos
        self.btnBuscarImagen.clicked.connect(
            lambda: self.seleccionar_archivo_corregido(
                self.label_imagen, self.lineEdit_imagen, 200, 150, "imagen_subseccion"
            )
        )
        
        self.btnBuscarFoto1.clicked.connect(
            lambda: self.seleccionar_archivo_corregido(
                self.label_foto_1, self.lineEdit_foto_1, 200, 150, "foto_subseccion"
            )
        )
        self.btnBuscarFoto2.clicked.connect(
            lambda: self.seleccionar_archivo_corregido(
                self.label_foto_2, self.lineEdit_foto_2, 200, 150, "foto_subseccion"
            )
        )
        self.btnBuscarFoto3.clicked.connect(
            lambda: self.seleccionar_archivo_corregido(
                self.label_foto_3, self.lineEdit_foto_3, 200, 150, "foto_subseccion"
            )
        )
        self.btnBuscarFoto4.clicked.connect(
            lambda: self.seleccionar_archivo_corregido(
                self.label_foto_4, self.lineEdit_foto_4, 200, 150, "foto_subseccion"
            )
        )

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
    # MANEJO DE REGIONES/ZONAS CON SISTEMA HÍBRIDO
    # -------------------------
    def cargar_regiones_zonas(self):
        """Carga las regiones/zonas habilitadas en el comboBox"""
        try:
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
        except Exception as e:
            # print(f"❌ Error cargando regiones/zonas: {e}")
            QMessageBox.warning(self, "Error", f"No se pudieron cargar las regiones/zonas: {e}")

    def on_region_zona_changed(self, index):
        """Maneja el cambio de selección en regiones/zonas"""
        if index == 0:
            self.label_imagen_region_zona.clear()
            self.region_zona_seleccionada = None
            self.comboBox_seccion.setEnabled(False)
            return
            
        id_region_zona = self.comboBox_region_zona.currentData()
        
        if not id_region_zona:
            return
            
        self.region_zona_seleccionada = id_region_zona
        
        # ✅ NUEVO: Cargar imagen usando sistema híbrido
        if id_region_zona in self.regiones_zonas_data:
            imagen_ruta_rel = self.regiones_zonas_data[id_region_zona]['imagen']
            
            if imagen_ruta_rel:
                ruta_encontrada = resolver_ruta_hibrida("", imagen_ruta_rel)
                if ruta_encontrada:
                    pixmap = cargar_imagen_desde_ruta(ruta_encontrada, (200, 150))
                    if pixmap and not pixmap.isNull():
                        self.label_imagen_region_zona.setPixmap(pixmap)
                        self.label_imagen_region_zona.setToolTip(f"Región/Zona: {self.regiones_zonas_data[id_region_zona]['nombre']}")
                    else:
                        self.mostrar_placeholder_imagen(self.label_imagen_region_zona, "Imagen no encontrada")
                else:
                    self.mostrar_placeholder_imagen(self.label_imagen_region_zona, "Sin imagen")
            else:
                self.mostrar_placeholder_imagen(self.label_imagen_region_zona, "Sin imagen")
        
        self.comboBox_seccion.setEnabled(True)
        self.cargar_sub_secciones()

    def mostrar_placeholder_imagen(self, label, texto):
        """Muestra un placeholder cuando no hay imagen"""
        label.clear()
        label.setText(texto)
        label.setStyleSheet("""
            QLabel {
                background-color: #f7fafc; 
                color: #4a5568; 
                border: 2px dashed #cbd5e0;
                font-weight: bold;
            }
        """)
        label.setAlignment(Qt.AlignCenter)

    # -------------------------
    # MANEJO DE SECCIONES CON SISTEMA HÍBRIDO
    # -------------------------
    def cargar_secciones_en_combo(self):
        """Carga las secciones en los combos y prepara datos de iconos"""
        try:
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
                
        except Exception as e:
            # print(f"❌ Error cargando secciones: {e}")
            QMessageBox.warning(self, "Error", f"No se pudieron cargar las secciones: {e}")

    def on_combo_seccion_changed(self, index):
        """Maneja el cambio de selección en secciones"""
        if self.edicion_subseccion:
            return
            
        sender = self.sender()
        id_seccion = sender.currentData()
        
        if id_seccion and id_seccion in self.secciones_data:
            icono_ruta = self.secciones_data[id_seccion]['icono']
            
            if icono_ruta:
                # ✅ NUEVO: Usar sistema híbrido para cargar icono
                ruta_encontrada = resolver_ruta_hibrida("", icono_ruta)
                
                if ruta_encontrada:
                    pixmap = cargar_imagen_desde_ruta(ruta_encontrada, (48, 48))
                    if pixmap and not pixmap.isNull():
                        self.label_icono.setPixmap(pixmap)
                        self.label_icono.setToolTip(f"Icono de: {self.secciones_data[id_seccion]['nombre']}")
                    else:
                        self.mostrar_placeholder_imagen(self.label_icono, "Icono no disponible")
                else:
                    self.mostrar_placeholder_imagen(self.label_icono, "Sin icono")
                
                self.lineEdit_icono.setText(icono_ruta)
            else:
                self.label_icono.clear()
                self.lineEdit_icono.clear()
                self.mostrar_placeholder_imagen(self.label_icono, "Sin icono")
        
        if sender == self.comboBox_seccion:
            self.cargar_sub_secciones()
        elif sender == self.comboBox_seccion1:
            self.cargar_sub_secciones_inactivas()

    # -------------------------
    # CARDS CON SISTEMA HÍBRIDO
    # -------------------------
    def crear_card(self, elemento, inactivo=False):
        """Crea una tarjeta visual para una subsección - CON SISTEMA HÍBRIDO"""
        card = QFrame()
        card.setFrameShape(QFrame.Box)
        card.setLineWidth(1)
        card.setFixedSize(220, 300)
        layout = QVBoxLayout(card)

        # Icono
        icono_label = QLabel()
        icono_label.setFixedSize(48, 48)
        icono_label.setAlignment(Qt.AlignCenter)
        ruta_icono = elemento.get("icono_ruta_relativa")
        self.cargar_imagen_hibrida(ruta_icono, icono_label, (48, 48), "Sin icono")
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
        ruta_img = elemento.get("imagen_ruta_relativa")
        self.cargar_imagen_hibrida(ruta_img, imagen_label, (180, 120), "Sin imagen")
        layout.addWidget(imagen_label)

        # Estado
        estado_label = QLabel("INACTIVO" if inactivo else "ACTIVO")
        estado_label.setAlignment(Qt.AlignCenter)
        estado_label.setStyleSheet("color: red;" if inactivo else "color: green;")
        layout.addWidget(estado_label)

        card.subseccion_id = elemento.get("id_sub_seccion")
        return card

    def cargar_imagen_hibrida(self, ruta_relativa, label_widget, size, fallback_text):
        """Carga imagen usando sistema híbrido REMOTO → LOCAL"""
        if not ruta_relativa:
            self.mostrar_placeholder_imagen(label_widget, fallback_text)
            return

        # ✅ NUEVO: Usar sistema híbrido
        ruta_encontrada = resolver_ruta_hibrida("", ruta_relativa)
        
        if ruta_encontrada:
            pixmap = cargar_imagen_desde_ruta(ruta_encontrada, size)
            if pixmap and not pixmap.isNull():
                label_widget.setPixmap(pixmap)
                label_widget.setStyleSheet("")
                label_widget.setToolTip(f"Imagen: {os.path.basename(ruta_encontrada)}")
            else:
                self.mostrar_placeholder_imagen(label_widget, fallback_text)
        else:
            self.mostrar_placeholder_imagen(label_widget, fallback_text)

    # -------------------------
    # CARGA DE SUBSECCIONES CON SISTEMA HÍBRIDO
    # -------------------------
    def cargar_sub_secciones(self):
        """Carga las subsecciones activas - CON SISTEMA HÍBRIDO"""
        # Limpiar layout
        for i in reversed(range(self.layout_activos.count())):
            item = self.layout_activos.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        id_seccion = self.comboBox_seccion.currentData()
        id_region_zona = self.region_zona_seleccionada

        if not id_seccion:
            return

        try:
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
                card = self.crear_card(fila)
                card.subseccion_id = fila.get("id_sub_seccion")
                card.mousePressEvent = lambda event, c=card: self.on_card_clicked(c)

                self.layout_activos.addWidget(card, row, col)
                col += 1
                if col >= 3:
                    col = 0
                    row += 1
                    
        except Exception as e:
            # print(f"❌ Error cargando subsecciones activas: {e}")
            QMessageBox.warning(self, "Error", f"No se pudieron cargar las subsecciones: {e}")

    def cargar_sub_secciones_inactivas(self):
        """Carga las subsecciones inactivas - CON SISTEMA HÍBRIDO"""
        # Limpiar layout
        for i in reversed(range(self.layout_inactivos.count())):
            item = self.layout_inactivos.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        id_seccion = self.comboBox_seccion1.currentData()
        id_region_zona = self.region_zona_seleccionada

        if not id_seccion:
            return

        try:
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
                card = self.crear_card(fila, inactivo=True)
                card.mousePressEvent = lambda event, f=fila: self.on_card_clicked_inactiva(f)

                self.layout_inactivos.addWidget(card, row, col)
                col += 1
                if col >= 3:
                    col = 0
                    row += 1
                    
        except Exception as e:
            # print(f"❌ Error cargando subsecciones inactivas: {e}")
            QMessageBox.warning(self, "Error", f"No se pudieron cargar las subsecciones inactivas: {e}")

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
            "id_region_zona": subseccion.get('id_region_zona'),
            "domicilio": subseccion.get('domicilio', ''),
            "latitud": subseccion.get('latitud'),
            "longitud": subseccion.get('longitud'),
            "distancia": subseccion.get('distancia', ''),
            "numero_telefono": subseccion.get('numero_telefono', ''),
            "imagen_rel": subseccion.get('imagen_ruta_relativa'),
            "icono_rel": subseccion.get('icono_ruta_relativa'),
            "foto1_rel": subseccion.get('foto1_ruta_relativa'),
            "foto2_rel": subseccion.get('foto2_ruta_relativa'),
            "foto3_rel": subseccion.get('foto3_ruta_relativa'),
            "foto4_rel": subseccion.get('foto4_ruta_relativa'),
            "itinerario_maps": subseccion.get('itinerario_maps', '')
        }

        self.cargar_sub_seccion_en_formulario(fila)

    def on_card_clicked_inactiva(self, fila):
        """Maneja el clic en una card inactiva (reactivación)"""
        if not fila:
            return

        self.id_subseccion_seleccionada = fila.get("id_sub_seccion")
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
    # FORMULARIO CON SISTEMA HÍBRIDO
    # -------------------------
    def cargar_sub_seccion_en_formulario(self, fila):
        """Carga los datos de una subsección en el formulario"""
        if not fila:
            return

        self.id_subseccion_seleccionada = fila.get("id_sub_seccion")

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

        # ✅ NUEVO: Cargar imágenes usando sistema híbrido
        self.cargar_imagen_formulario_hibrida(self.label_imagen, fila.get("imagen_rel"), (200,150))
        self.cargar_imagen_formulario_hibrida(self.label_icono, fila.get("icono_rel"), (48,48))
        self.cargar_imagen_formulario_hibrida(self.label_foto_1, fila.get("foto1_rel"), (200,150))
        self.cargar_imagen_formulario_hibrida(self.label_foto_2, fila.get("foto2_rel"), (200,150))
        self.cargar_imagen_formulario_hibrida(self.label_foto_3, fila.get("foto3_rel"), (200,150))
        self.cargar_imagen_formulario_hibrida(self.label_foto_4, fila.get("foto4_rel"), (200,150))

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

    def cargar_imagen_formulario_hibrida(self, label_widget, ruta_rel, size):
        """Carga una imagen en el formulario usando sistema híbrido"""
        tooltip = f"Ruta relativa: {ruta_rel or 'No disponible'}"
        label_widget.setToolTip(tooltip)

        if ruta_rel:
            # ✅ NUEVO: Usar sistema híbrido
            ruta_encontrada = resolver_ruta_hibrida("", ruta_rel)
            if ruta_encontrada:
                pixmap = cargar_imagen_desde_ruta(ruta_encontrada, size)
                if pixmap and not pixmap.isNull():
                    label_widget.setPixmap(pixmap)
                    label_widget.setStyleSheet("")
                else:
                    self.mostrar_placeholder_imagen(label_widget, "Imagen no disponible")
            else:
                self.mostrar_placeholder_imagen(label_widget, "Sin imagen")
        else:
            self.mostrar_placeholder_imagen(label_widget, "Sin imagen")

    # -------------------------
    # SELECCIÓN DE ARCHIVOS
    # -------------------------
    def seleccionar_archivo_corregido(self, label_obj, lineedit_obj, ancho, alto, tipo_archivo):
        """Abre diálogo para seleccionar archivo y lo procesa para producción"""
        archivo, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo", "", 
            "Medios soportados (*.png *.jpg *.jpeg *.bmp *.mp4 *.webm *.ogg);;"
            "Imágenes (*.png *.jpg *.jpeg *.bmp);;"
            "Videos (*.mp4 *.webm *.ogg)"
        )
        if not archivo:
            return

        # Convertir a ruta de producción
        ruta_relativa_produccion = convertir_ruta_produccion(archivo)
        
        if not ruta_relativa_produccion:
            QMessageBox.warning(self, "Error", "No se pudo procesar el archivo seleccionado")
            return

        # Mostrar preview según el tipo de archivo
        es_video = archivo.lower().endswith(('.mp4', '.webm', '.ogg'))
        
        if es_video:
            # Para videos: mostrar ícono/thumbnail
            label_obj.clear()
            label_obj.setText("🎬 Video\nSeleccionado")
            label_obj.setStyleSheet("background-color: #2d3748; color: #90cdf4; font-weight: bold; border: 2px dashed #4a5568;")
            label_obj.setAlignment(Qt.AlignCenter)
        else:
            # Para imágenes: mostrar preview normal
            try:
                pixmap = QPixmap(archivo).scaled(ancho, alto, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label_obj.setPixmap(pixmap)
                label_obj.setStyleSheet("")  # Resetear estilo
            except Exception as e:
                label_obj.clear()
                label_obj.setText("Error\ncargando\nimagen")
                label_obj.setStyleSheet("background-color: #fed7d7; color: #c53030;")
                # print(f"Error cargando imagen preview: {e}")

        # Guardar ruta de producción en el lineedit
        lineedit_obj.setText(ruta_relativa_produccion)
        
        tooltip_text = f"Ruta producción: {ruta_relativa_produccion}"
        if es_video:
            tooltip_text += f"\nTipo: Video ({os.path.basename(archivo).split('.')[-1].upper()})"
        else:
            tooltip_text += f"\nTipo: Imagen"
        
        label_obj.setToolTip(tooltip_text)

        # Actualizar automáticamente en BD si hay subsección seleccionada
        if self.id_subseccion_seleccionada:
            self.actualizar_ruta_en_bd(tipo_archivo, ruta_relativa_produccion, lineedit_obj)

    def actualizar_ruta_en_bd(self, tipo_archivo, ruta_relativa, lineedit_obj=None):
        """Actualiza automáticamente la ruta en la base de datos"""
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            
            # Determinar campo a actualizar según tipo de archivo
            campo = "imagen_ruta_relativa"  # valor por defecto
            
            if tipo_archivo == "imagen_subseccion":
                campo = "imagen_ruta_relativa"
            elif tipo_archivo == "foto_subseccion":
                # Determinar qué foto actualizar basado en el lineedit
                if lineedit_obj:
                    if lineedit_obj == self.lineEdit_foto_1:
                        campo = "foto1_ruta_relativa"
                    elif lineedit_obj == self.lineEdit_foto_2:
                        campo = "foto2_ruta_relativa"
                    elif lineedit_obj == self.lineEdit_foto_3:
                        campo = "foto3_ruta_relativa"
                    elif lineedit_obj == self.lineEdit_foto_4:
                        campo = "foto4_ruta_relativa"
            
            cursor.execute(f"""
                UPDATE sub_secciones
                SET {campo} = %s
                WHERE id_sub_seccion = %s
            """, (ruta_relativa, self.id_subseccion_seleccionada))
            
            conexion.commit()
            conexion.close()
            
            # print(f"✅ {campo} actualizado en BD: {ruta_relativa}")
            
        except Exception as e:
            # print(f"❌ Error actualizando BD: {e}")
            QMessageBox.warning(self, "Error BD", f"No se pudo actualizar la ruta en la base de datos:\n{e}")

    # -------------------------
    # OPERACIONES CRUD (se mantienen igual)
    # -------------------------
    def agregar_sub_seccion(self):
        """Agrega una nueva subsección con rutas de producción"""
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

        # Usar rutas relativas directamente
        imagen_rel = self.lineEdit_imagen.text().strip() or None
        icono_rel = self.lineEdit_icono.text().strip() or None
        foto1_rel = self.lineEdit_foto_1.text().strip() or None
        foto2_rel = self.lineEdit_foto_2.text().strip() or None
        foto3_rel = self.lineEdit_foto_3.text().strip() or None
        foto4_rel = self.lineEdit_foto_4.text().strip() or None

        # Resto de campos
        domicilio = self.lineEdit_domicilio.text().strip()
        distancia = self.lineEdit_distancia.text().strip()
        telefono = self.lineEdit_numero_telefono.text().strip()
        itinerario = self.lineEdit_itinerario.text().strip()
        habilitar = 1
        orden = self.spinBox_orden.value()
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

        # Insertar en DB
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO sub_secciones 
                (id_seccion, id_region_zona, nombre_sub_seccion, domicilio, latitud, longitud, 
                distancia, numero_telefono, imagen_ruta_relativa, icono_ruta_relativa, 
                itinerario_maps, habilitar, fecha_desactivacion, orden, destacado,
                foto1_ruta_relativa, foto2_ruta_relativa, foto3_ruta_relativa, foto4_ruta_relativa)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                id_seccion, id_region_zona, nombre, domicilio, latitud, longitud, 
                distancia, telefono, imagen_rel, icono_rel, 
                itinerario, habilitar, fecha, orden, destacado,
                foto1_rel, foto2_rel, foto3_rel, foto4_rel
            ))
            conexion.commit()
            conexion.close()

            QMessageBox.information(self, "Éxito", "Subsección agregada correctamente")
            self.limpiar_formulario()
            self.cargar_sub_secciones()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo agregar la subsección: {str(e)}")

    def modificar_sub_seccion(self):
        """Modifica una subsección existente con rutas de producción"""
        if not self.id_subseccion_seleccionada:
            QMessageBox.warning(self, "Error", "Seleccione una subsección para modificar")
            return

        # Usar rutas relativas directamente
        imagen_rel = self.lineEdit_imagen.text().strip() or None
        icono_rel = self.lineEdit_icono.text().strip() or None
        foto1_rel = self.lineEdit_foto_1.text().strip() or None
        foto2_rel = self.lineEdit_foto_2.text().strip() or None
        foto3_rel = self.lineEdit_foto_3.text().strip() or None
        foto4_rel = self.lineEdit_foto_4.text().strip() or None

        # Resto de campos
        nombre = self.lineEdit_nombre_subSeccion.text().strip()
        domicilio = self.lineEdit_domicilio.text().strip()
        distancia = self.lineEdit_distancia.text().strip()
        telefono = self.lineEdit_numero_telefono.text().strip()
        itinerario = self.lineEdit_itinerario.text().strip()
        habilitar = 1
        orden = self.spinBox_orden.value()
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
                    imagen_ruta_relativa = %s,
                    icono_ruta_relativa = %s,
                    itinerario_maps = %s,
                    habilitar = %s,
                    fecha_desactivacion = %s,
                    orden = %s,
                    destacado = %s,
                    foto1_ruta_relativa = %s,
                    foto2_ruta_relativa = %s,
                    foto3_ruta_relativa = %s,
                    foto4_ruta_relativa = %s
                WHERE id_sub_seccion = %s
            """, (
                id_seccion, id_region_zona, nombre, domicilio, latitud, longitud, 
                distancia, telefono, imagen_rel, icono_rel, 
                itinerario, habilitar, fecha, orden, destacado,
                foto1_rel, foto2_rel, foto3_rel, foto4_rel,
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
            self.mostrar_placeholder_imagen(label, "Sin imagen")

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