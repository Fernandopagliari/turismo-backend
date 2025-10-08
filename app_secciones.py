# -*- coding: utf-8 -*-
from PyQt5 import uic
from database_hosting import conectar_hosting as conectar_base_datos, cerrar_conexion
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QApplication, QWidget, QMessageBox
from PyQt5.QtGui import QPixmap, QPainter, QPainterPath
from PyQt5.QtCore import Qt, QRectF
import os
import shutil
import hashlib

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
        self.lineEdit_icono_seccion.setText(item(fila, 2).text() if item(fila, 2) else "")
        self.spinBox_orden_seccion.setValue(int(item(fila, 3).text()) if item(fila, 3) else 0)

        # Mostrar icono
        ruta_relativa = item(fila, 2).text() if item(fila, 2) else ""
        if ruta_relativa:
            # Convertir a ruta absoluta, asegurando que la barra inicial no sea un problema
            ruta_relativa = ruta_relativa.lstrip("/\\")  # elimina barras al inicio
            ruta_absoluta = os.path.join(os.getcwd(), "public", ruta_relativa.replace("/", os.sep))
            
            if os.path.exists(ruta_absoluta):
                pixmap_icono = self.cargar_imagen_en_label(ruta_absoluta, self.label_icono_seccion, size=75, circular=True)
                self.label_icono_seccion.setPixmap(pixmap_icono)
                self.label_icono_seccion.setText("")
            else:
                self.label_icono_seccion.clear()
                self.label_icono_seccion.setText("Sin icono")
        else:
            self.label_icono_seccion.clear()
            self.label_icono_seccion.setText("Sin icono")


        self.btnAgregarSeccion.setEnabled(False)
        self.btnModificarSeccion.setEnabled(True)
        self.btnEliminarSeccion.setEnabled(True)
        self.btnDesactivarSeccion.setEnabled(True)
        self.btnReactivarSeccion.setEnabled(False)

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
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO secciones (nombre_seccion, icono_seccion, orden, habilitar)
                VALUES (%s, %s, %s, 1)
            """, (nombre, icono, orden))
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
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE secciones
                SET nombre_seccion=%s, icono_seccion=%s, orden=%s
                WHERE id_seccion=%s
            """, (
                self.lineEdit_nombre_seccion_app.text(),
                self.lineEdit_icono_seccion.text(),
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

        # Carpeta destino: ahora dentro de /assets/imagenes/iconos
        carpeta_destino = os.path.join(os.getcwd(), "public", "assets", "imagenes", "iconos")
        os.makedirs(carpeta_destino, exist_ok=True)  # Aseguramos que exista

        nombre_archivo = os.path.basename(ruta_origen)
        nombre_base, extension = os.path.splitext(nombre_archivo)
        ruta_destino = os.path.join(carpeta_destino, nombre_archivo)

        try:
            if os.path.exists(ruta_destino) and os.path.samefile(ruta_origen, ruta_destino):
                ruta_final = ruta_destino
            else:
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

                shutil.copy(ruta_origen, ruta_destino)
                ruta_final = ruta_destino

        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo copiar el icono:\n{e}")
            return

        # Guardamos la ruta relativa correcta (con imágenes/iconos)
        ruta_relativa = f"/assets/imagenes/iconos/{os.path.basename(ruta_destino)}"
        self.lineEdit_icono_seccion.setText(ruta_relativa)

        # Mostrar icono
        pixmap_icono = self.cargar_imagen_en_label(ruta_final, self.label_icono_seccion, size=75, circular=True)
        self.label_icono_seccion.setPixmap(pixmap_icono)
        self.label_icono_seccion.setText("")


    # ------------------ Función reusable para imágenes -------------------
    def cargar_imagen_en_label(self, ruta_imagen, label=None, size=75, circular=True, center=True):
        """
        Carga una imagen en un QLabel, opcionalmente la recorta circular y ajusta tamaño.
        Devuelve el QPixmap resultante.
        """
        pixmap = QPixmap(ruta_imagen)
        if pixmap.isNull():
            return QPixmap()

        pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        if circular:
            mask = QPixmap(size, size)
            mask.fill(Qt.transparent)
            painter = QPainter(mask)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addEllipse(QRectF(0, 0, size, size))
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            pixmap = mask

        if center and label:
            label.setAlignment(Qt.AlignCenter)

        if label:
            label.setPixmap(pixmap)
        return pixmap
