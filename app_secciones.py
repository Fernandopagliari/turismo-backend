# -*- coding: utf-8 -*-
from PyQt5 import uic
from database_hosting import conectar_hosting as conectar_base_datos, cerrar_conexion
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QApplication, QWidget, QMessageBox
from PyQt5.QtGui import QPixmap, QPainter, QPainterPath
from PyQt5.QtCore import Qt, QRectF
import os
import shutil
import hashlib
import requests

# -------------------------
# MÉTODOS DE BÚSQUEDA HÍBRIDA (igual que en ventana_principal)
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
            print(f"✅ [SECCIONES] Encontrado en REMOTO: {url_remota}")
            return url_remota
    
    # 2. SEGUNDO: Buscar en LOCAL con ruta absoluta
    if ruta_absoluta_db and os.path.exists(ruta_absoluta_db):
        print(f"✅ [SECCIONES] Encontrado en LOCAL: {ruta_absoluta_db}")
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
                print(f"✅ [SECCIONES] Encontrado en PROYECTO: {ruta}")
                return ruta
    
    print(f"❌ [SECCIONES] No encontrado: {ruta_relativa_db}")
    return ""

def cargar_imagen_desde_ruta(ruta_imagen: str, size: int = 75):
    """
    Carga imagen desde URL remota o archivo local
    """
    if not ruta_imagen:
        return None

    try:
        # ✅ MANEJAR URL REMOTA (AGREGAR TIMEOUT)
        if _is_url(ruta_imagen):
            response = requests.get(ruta_imagen, timeout=8)  # ⬅️ AGREGAR ESTO
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                if not pixmap.isNull():
                    print(f"✅ [SECCIONES] Imagen remota cargada: {ruta_imagen}")
                    return pixmap
            return None
        
        # ✅ MANEJAR ARCHIVO LOCAL
        elif os.path.exists(ruta_imagen):
            pixmap = QPixmap(ruta_imagen)
            if not pixmap.isNull():
                print(f"✅ [SECCIONES] Imagen local cargada: {ruta_imagen}")
                return pixmap
        
        return None
        
    except Exception as e:
        print(f"❌ [SECCIONES] Error cargando imagen: {e}")
        return None

def ruta_absoluta_desde_relativa(relativa):
    """
    Convierte '/assets/...png' a la ruta absoluta correcta.
    """
    if not relativa:
        return ""
    # Subimos dos niveles desde src/backend a la raíz del proyecto
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  
    base_assets = os.path.join(base_dir, "frontend", "public")
    return os.path.join(base_assets, relativa.lstrip("/"))

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

class VentanaSecciones(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlag(Qt.Window)
        self.resize(700, 500)
        self.centrar_ventana()
        self.parent_widget = parent

        # Ruta absoluta al archivo .ui
        ruta_ui = os.path.join(os.path.dirname(__file__), "interfaz", "secciones_app.ui")
        if not os.path.exists(ruta_ui):
            raise FileNotFoundError(f"No se encontró el archivo UI en: {ruta_ui}")

        uic.loadUi(ruta_ui, self)
        self.setWindowTitle("Gestión de Secciones")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMinMaxButtonsHint)

        # Cargar secciones
        self.cargar_secciones_activas()
        self.cargar_secciones_inactivas()

        # Conectar botones
        self.btnAgregarSeccion.clicked.connect(self.agregar_seccion)
        self.btnModificarSeccion.clicked.connect(self.modificar_seccion)
        self.btnEliminarSeccion.clicked.connect(self.eliminar_seccion)
        self.btnDesactivarSeccion.clicked.connect(self.desactivar_seccion)
        self.btnReactivarSeccion.clicked.connect(self.reactivar_seccion)
        self.btnLimpiarFormulario.clicked.connect(self.limpiar_formulario)
        self.btnIconoSeccion.clicked.connect(self.seleccionar_icono)
        self.btnCerrar.clicked.connect(self.close)

        # Eventos al seleccionar fila
        self.Tabla_secciones_activas.cellClicked.connect(self.seleccionar_seccion_activa)
        self.Tabla_secciones_inactivas.cellClicked.connect(self.seleccionar_seccion_inactiva)

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

    def cargar_secciones_activas(self):
        conexion = conectar_base_datos()
        cursor = conexion.cursor()
        cursor.execute("SELECT id_seccion, nombre_seccion, icono_seccion, orden FROM secciones WHERE habilitar = 1 ORDER BY orden ASC")
        resultados = cursor.fetchall()
        conexion.close()

        columnas = ["ID", "Nombre", "Icono", "Orden"]
        self.Tabla_secciones_activas.setColumnCount(len(columnas))
        self.Tabla_secciones_activas.setHorizontalHeaderLabels(columnas)
        self.Tabla_secciones_activas.setRowCount(0)

        for row_number, row_data in enumerate(resultados):
            self.Tabla_secciones_activas.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                item = QTableWidgetItem(str(data))
                self.Tabla_secciones_activas.setItem(row_number, column_number, item)

    def cargar_secciones_inactivas(self):
        conexion = conectar_base_datos()
        cursor = conexion.cursor()
        cursor.execute("SELECT id_seccion, nombre_seccion, icono_seccion, orden FROM secciones WHERE habilitar = 0 ORDER BY orden ASC")
        resultados = cursor.fetchall()
        conexion.close()

        columnas = ["ID", "Nombre", "Icono", "Orden"]
        self.Tabla_secciones_inactivas.setColumnCount(len(columnas))
        self.Tabla_secciones_inactivas.setHorizontalHeaderLabels(columnas)
        self.Tabla_secciones_inactivas.setRowCount(0)

        for row_number, row_data in enumerate(resultados):
            self.Tabla_secciones_inactivas.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                item = QTableWidgetItem(str(data))
                self.Tabla_secciones_inactivas.setItem(row_number, column_number, item)

    def seleccionar_seccion_activa(self, fila, columna):
        item = lambda f, c: self.Tabla_secciones_activas.item(f, c)
        self.seccion_seleccionada_id = item(fila, 0).text() if item(fila, 0) else ""
        self.lineEdit_nombre_seccion_app.setText(item(fila, 1).text() if item(fila, 1) else "")
        
        # ✅ NUEVO: Usar búsqueda híbrida para el icono
        ruta_relativa = item(fila, 2).text() if item(fila, 2) else ""
        ruta_encontrada = resolver_ruta_hibrida("", ruta_relativa)  # Solo necesitamos la ruta relativa
        
        self.lineEdit_icono_seccion.setText(ruta_encontrada)
        self.spinBox_orden_seccion.setValue(int(item(fila, 3).text()) if item(fila, 3) else 0)

        # Mostrar icono con soporte para URLs remotas
        if ruta_encontrada:
            self.mostrar_icono_seccion(ruta_encontrada)
        else:
            self.label_icono_seccion.clear()
            self.label_icono_seccion.setText("Sin icono")

        self.btnAgregarSeccion.setEnabled(False)
        self.btnModificarSeccion.setEnabled(True)
        self.btnEliminarSeccion.setEnabled(True)
        self.btnDesactivarSeccion.setEnabled(True)
        self.btnReactivarSeccion.setEnabled(False)

    def mostrar_icono_seccion(self, ruta_imagen: str):
        """
        NUEVO: Muestra icono de sección desde URL remota o archivo local
        """
        pixmap = cargar_imagen_desde_ruta(ruta_imagen, 75)
        if pixmap and not pixmap.isNull():
            pixmap_redondeada = self.redondear_imagen_pixmap(pixmap, 75)
            self.label_icono_seccion.setPixmap(pixmap_redondeada)
            self.label_icono_seccion.setText("")
            self.label_icono_seccion.setAlignment(Qt.AlignCenter)
        else:
            self.label_icono_seccion.clear()
            self.label_icono_seccion.setText("Sin icono")

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
        path.addEllipse(QRectF(0, 0, size, size))
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        
        return mask

    def seleccionar_seccion_inactiva(self, fila, columna):
        item = self.Tabla_secciones_inactivas.item(fila, 0)
        if item:
            self.seccion_inactiva_id = item.text()
            self.btnReactivarSeccion.setEnabled(True)

    def agregar_seccion(self):
        nombre = self.lineEdit_nombre_seccion_app.text().strip()
        icono = self.lineEdit_icono_seccion.text().strip()
        orden = self.spinBox_orden_seccion.value()
        
        if not nombre:
            QMessageBox.warning(self, "Campos obligatorios", "Debes ingresar un nombre de sección.")
            return
        
        # ✅ CORREGIDO: Convertir ruta absoluta a ruta de producción
        ruta_absoluta_actual = icono
        ruta_relativa_corregida = convertir_ruta_produccion(ruta_absoluta_actual) if ruta_absoluta_actual and not _is_url(ruta_absoluta_actual) else ""
        
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO secciones (nombre_seccion, icono_seccion, orden, habilitar)
                VALUES (%s, %s, %s, 1)
            """, (nombre, ruta_relativa_corregida, orden))  # ✅ Usar ruta corregida
            conexion.commit()
            conexion.close()
            QMessageBox.information(self, "Sección", "Sección agregada correctamente.")
            self.cargar_secciones_activas()
            self.limpiar_formulario()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo agregar sección:\n{str(e)}")
            
    def modificar_seccion(self):
        if not hasattr(self, 'seccion_seleccionada_id') or not self.seccion_seleccionada_id:
            QMessageBox.warning(self, "Modificar", "Seleccione una sección para modificar.")
            return
        
        # ✅ CORREGIDO: Convertir ruta absoluta a ruta de producción
        ruta_absoluta_actual = self.lineEdit_icono_seccion.text().strip()
        ruta_relativa_corregida = convertir_ruta_produccion(ruta_absoluta_actual) if ruta_absoluta_actual and not _is_url(ruta_absoluta_actual) else ""
        
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE secciones
                SET nombre_seccion=%s, icono_seccion=%s, orden=%s
                WHERE id_seccion=%s
            """, (
                self.lineEdit_nombre_seccion_app.text(),
                ruta_relativa_corregida,  # ✅ Usar ruta corregida
                self.spinBox_orden_seccion.value(),
                self.seccion_seleccionada_id
            ))
            conexion.commit()
            conexion.close()
            QMessageBox.information(self, "Sección", "Sección modificada correctamente.")
            self.cargar_secciones_activas()
            self.limpiar_formulario()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo modificar sección:\n{str(e)}")

    def eliminar_seccion(self):
        try:
            id_seccion = self.seccion_seleccionada_id
            if not id_seccion:
                QMessageBox.warning(self, "Error", "Debe seleccionar una sección para eliminar")
                return
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("SELECT nombre_seccion FROM secciones WHERE id_seccion = %s", (id_seccion,))
            seccion = cursor.fetchone()
            if not seccion:
                QMessageBox.warning(self, "Error", f"No se encontró ninguna sección con ID {id_seccion}")
                return
            nombre_seccion = seccion[0]
            cursor.execute("SELECT nombre_sub_seccion FROM sub_secciones WHERE id_seccion = %s", (id_seccion,))
            subsecciones = cursor.fetchall()
            if subsecciones:
                lista_subs = "\n".join([s[0] for s in subsecciones])
                QMessageBox.information(
                    self, "Sección con subsecciones",
                    f"La sección '{nombre_seccion}' tiene las siguientes subsecciones asociadas:\n\n{lista_subs}\n\nDebes reasignar o eliminar estas subsecciones antes de poder borrar la sección."
                )
                return
            confirmacion = QMessageBox.question(
                self, "Confirmar eliminación",
                f"¿Estás seguro que deseas eliminar la sección '{nombre_seccion}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirmacion != QMessageBox.Yes:
                return
            cursor.execute("DELETE FROM secciones WHERE id_seccion=%s", (id_seccion,))
            conexion.commit()
            QMessageBox.information(self, "Éxito", f"La sección '{nombre_seccion}' fue eliminada correctamente.")
            self.cargar_secciones_activas()
            self.limpiar_formulario()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar la sección:\n{e}")
        finally:
            if cursor:
                cursor.close()
            if conexion:
                conexion.close()

    def desactivar_seccion(self):
        if not hasattr(self, 'seccion_seleccionada_id') or not self.seccion_seleccionada_id:
            QMessageBox.warning(self, "Desactivar", "Seleccione una sección para desactivar.")
            return
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("UPDATE secciones SET habilitar=0 WHERE id_seccion=%s", (self.seccion_seleccionada_id,))
            conexion.commit()
            conexion.close()
            QMessageBox.information(self, "Sección", "Sección desactivada correctamente.")
            self.cargar_secciones_activas()
            self.cargar_secciones_inactivas()
            self.limpiar_formulario()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo desactivar sección:\n{str(e)}")     

    def reactivar_seccion(self):
        if not hasattr(self, 'seccion_inactiva_id') or not self.seccion_inactiva_id:
            QMessageBox.warning(self, "Reactivar", "Seleccione una sección inactiva.")
            return
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("UPDATE secciones SET habilitar=1 WHERE id_seccion=%s", (self.seccion_inactiva_id,))
            conexion.commit()
            conexion.close()
            QMessageBox.information(self, "Sección", "Sección reactivada correctamente.")
            self.cargar_secciones_activas()
            self.cargar_secciones_inactivas()
            self.seccion_inactiva_id = None
            self.btnReactivarSeccion.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo reactivar sección:\n{str(e)}")

    def limpiar_formulario(self):
        self.lineEdit_nombre_seccion_app.clear()
        self.lineEdit_icono_seccion.clear()
        self.spinBox_orden_seccion.setValue(0)
        self.label_icono_seccion.clear()
        self.label_icono_seccion.setText("Sin icono")
        self.seccion_seleccionada_id = None
        self.seccion_inactiva_id = None
        self.btnAgregarSeccion.setEnabled(True)
        self.btnModificarSeccion.setEnabled(False)
        self.btnEliminarSeccion.setEnabled(True)
        self.btnDesactivarSeccion.setEnabled(False)
        self.btnReactivarSeccion.setEnabled(False)

    # ------------------ Imagenes -------------------

    def seleccionar_icono(self):
        # Selección del archivo
        ruta_origen, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar icono de sección", "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif)"
        )

        if not ruta_origen:
            self.lineEdit_icono_seccion.clear()
            self.label_icono_seccion.clear()
            self.label_icono_seccion.setText("Sin icono")
            return

        # ✅ CORREGIDO: Carpeta destino para React production
        carpeta_destino = os.path.join(os.getcwd(), "public", "assets", "imagenes", "iconos")
        os.makedirs(carpeta_destino, exist_ok=True)

        nombre_archivo = os.path.basename(ruta_origen)
        nombre_base, extension = os.path.splitext(nombre_archivo)
        ruta_destino = os.path.join(carpeta_destino, nombre_archivo)

        try:
            # ✅ Verificamos si el archivo ya está en la carpeta destino
            if os.path.abspath(ruta_origen) == os.path.abspath(ruta_destino):
                ruta_final = ruta_destino  # ya está en la carpeta correcta, no copiamos nada
            else:
                # Si existe y es distinto → renombrar
                def hash_archivo(path):
                    hasher = hashlib.md5()
                    with open(path, "rb") as f:
                        while chunk := f.read(8192):
                            hasher.update(chunk)
                    return hasher.hexdigest()

                if os.path.exists(ruta_destino):
                    if hash_archivo(ruta_destino) != hash_archivo(ruta_origen):
                        contador = 1
                        while True:
                            nuevo_nombre = f"{nombre_base}_{contador}{extension}"
                            nueva_ruta = os.path.join(carpeta_destino, nuevo_nombre)
                            if not os.path.exists(nueva_ruta):
                                ruta_destino = nueva_ruta
                                break
                            contador += 1

                # Copiar archivo
                shutil.copy(ruta_origen, ruta_destino)
                ruta_final = ruta_destino

        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo copiar el icono:\n{e}")
            return

        # ✅ CORREGIDO: Usar función helper para ruta de producción
        ruta_relativa = convertir_ruta_produccion(ruta_final)
        
        # Mostrar ruta absoluta en el lineEdit (para visualización local)
        self.lineEdit_icono_seccion.setText(ruta_final)

        # Mostrar icono con soporte para búsqueda híbrida
        self.mostrar_icono_seccion(ruta_final)

        # ✅ CORREGIDO: Si hay una sección seleccionada, actualizar en BD con ruta de producción
        if hasattr(self, 'seccion_seleccionada_id') and self.seccion_seleccionada_id:
            try:
                conexion = conectar_base_datos()
                cursor = conexion.cursor()
                cursor.execute("""
                    UPDATE secciones
                    SET icono_seccion=%s
                    WHERE id_seccion=%s
                """, (ruta_relativa, self.seccion_seleccionada_id))
                conexion.commit()
                conexion.close()
                print(f"✅ Icono actualizado en BD: {ruta_relativa}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo actualizar el icono en BD:\n{e}")
        else:
            # Si no hay sección seleccionada, solo mostrar mensaje informativo
            print(f"ℹ️  Icono preparado para nueva sección: {ruta_relativa}")