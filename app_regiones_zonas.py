# -*- coding: utf-8 -*-
from PyQt5 import uic
from database_hosting import conectar_hosting as conectar_base_datos
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
    base_dir = os.path.dirname(os.path.dirname(__file__))  # subimos 2 niveles hasta la raíz
    base_assets = os.path.join(base_dir, "public")         # la carpeta real es "public"
    return os.path.join(base_assets, relativa.lstrip("/"))



class VentanaRegionesZonas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlag(Qt.Window)
        self.resize(700, 500)
        self.centrar_ventana()
        self.parent_widget = parent

        # Variables para mantener selección
        self.region_zona_seleccionada_id = None
        self.region_zona_inactiva_id = None

        # Cargar interfaz
        ruta_ui = os.path.join(os.path.dirname(__file__), "interfaz", "regiones_zonas_app.ui")
        if not os.path.exists(ruta_ui):
            raise FileNotFoundError(f"No se encontró el archivo UI en: {ruta_ui}")

        uic.loadUi(ruta_ui, self)
        self.setWindowTitle("Gestión de Regiones/Zonas")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMinMaxButtonsHint)

        # Cargar datos
        self.cargar_regiones_zonas_activas()
        self.cargar_regiones_zonas_inactivas()

        # Conectar botones
        self.btnAgregarRegionZona.clicked.connect(self.agregar_region_zona)
        self.btnModificarRegionZona.clicked.connect(self.modificar_region_zona)
        self.btnEliminarRegionZona.clicked.connect(self.eliminar_region_zona)
        self.btnDesactivarRegionZona.clicked.connect(self.desactivar_region_zona)
        self.btnReactivarRegionZona.clicked.connect(self.reactivar_region_zona)
        self.btnLimpiarFormulario.clicked.connect(self.limpiar_formulario)
        self.btnImagenRegionZona.clicked.connect(self.seleccionar_imagen_region_zona)
        self.btnCerrar.clicked.connect(self.close)

        # Eventos tabla
        self.Tabla_RegionZona_activas.cellClicked.connect(self.seleccionar_RegionZona_activa)
        self.Tabla_RegionZona_inactivas.cellClicked.connect(self.seleccionar_RegionZona_inactiva)

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

    def cargar_regiones_zonas_activas(self):
        conexion = conectar_base_datos()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT id_region_zona, nombre_region_zona, imagen_region_zona_ruta_relativa, orden 
            FROM regiones_zonas WHERE habilitar = 1 ORDER BY orden ASC
        """)
        resultados = cursor.fetchall()
        conexion.close()

        columnas = ["ID", "Nombre Región/Zona", "Ruta Imagen", "Orden"]
        self.Tabla_RegionZona_activas.setColumnCount(len(columnas))
        self.Tabla_RegionZona_activas.setHorizontalHeaderLabels(columnas)
        self.Tabla_RegionZona_activas.setRowCount(0)

        for row_number, row_data in enumerate(resultados):
            self.Tabla_RegionZona_activas.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                item = QTableWidgetItem(str(data if data is not None else ""))
                self.Tabla_RegionZona_activas.setItem(row_number, column_number, item)

    def cargar_regiones_zonas_inactivas(self):
        conexion = conectar_base_datos()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT id_region_zona, nombre_region_zona, imagen_region_zona_ruta_relativa, orden 
            FROM regiones_zonas WHERE habilitar = 0 ORDER BY orden ASC
        """)
        resultados = cursor.fetchall()
        conexion.close()

        columnas = ["ID", "Nombre Región/Zona", "Ruta Imagen", "Orden"]
        self.Tabla_RegionZona_inactivas.setColumnCount(len(columnas))
        self.Tabla_RegionZona_inactivas.setHorizontalHeaderLabels(columnas)
        self.Tabla_RegionZona_inactivas.setRowCount(0)

        for row_number, row_data in enumerate(resultados):
            self.Tabla_RegionZona_inactivas.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                item = QTableWidgetItem(str(data if data is not None else ""))
                self.Tabla_RegionZona_inactivas.setItem(row_number, column_number, item)

    def seleccionar_RegionZona_activa(self, fila, columna):
        item = lambda f, c: self.Tabla_RegionZona_activas.item(f, c)
        self.region_zona_seleccionada_id = item(fila, 0).text() if item(fila, 0) else ""
        self.lineEdit_nombre_region_zona.setText(item(fila, 1).text() if item(fila, 1) else "")
        self.lineEdit_ruta_imagen_region_zona.setText(item(fila, 2).text() if item(fila, 2) else "")
        self.spinBox_orden_region_zona.setValue(int(item(fila, 3).text()) if item(fila, 3) else 0)

        # Mostrar imagen
        ruta_relativa = item(fila, 2).text() if item(fila, 2) else ""
        print(f"[DEBUG] Ruta relativa: {ruta_relativa}")

        if ruta_relativa:
            ruta_absoluta = ruta_absoluta_desde_relativa(ruta_relativa)
            print(f"[DEBUG] Ruta absoluta: {ruta_absoluta}")
            
            if os.path.exists(ruta_absoluta):
                pixmap_imagen = self.cargar_imagen_en_label(ruta_absoluta, self.label_imagen_region_zona, size=75, circular=True)
                self.label_imagen_region_zona.setPixmap(pixmap_imagen)
                self.label_imagen_region_zona.setText("")
            else:
                print("[DEBUG] No existe la ruta absoluta")
                self.label_imagen_region_zona.clear()
                self.label_imagen_region_zona.setText("Sin icono")


        self.btnAgregarRegionZona.setEnabled(False)
        self.btnModificarRegionZona.setEnabled(True)
        self.btnEliminarRegionZona.setEnabled(True)
        self.btnDesactivarRegionZona.setEnabled(True)
        self.btnReactivarRegionZona.setEnabled(False)


    def seleccionar_RegionZona_inactiva(self, fila, columna):
        item = self.Tabla_RegionZona_inactivas.item(fila, 0)
        if item:
            self.region_zona_inactiva_id = item.text()
            self.btnReactivarRegionZona.setEnabled(True)

    def agregar_region_zona(self):
        nombre = self.lineEdit_nombre_region_zona.text().strip()
        imagen = self.lineEdit_ruta_imagen_region_zona.text().strip()
        orden = self.spinBox_orden_region_zona.value()

        if not nombre:
            QMessageBox.warning(self, "Campos obligatorios", "Debes ingresar un nombre de región/zona.")
            return

        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO regiones_zonas (nombre_region_zona, imagen_region_zona_ruta_relativa, orden, habilitar)
                VALUES (%s, %s, %s, 1)
            """, (nombre, imagen or None, orden))
            conexion.commit()
            conexion.close()
            QMessageBox.information(self, "Región/Zona", "Región/Zona agregada correctamente.")
            self.cargar_regiones_zonas_activas()
            self.limpiar_formulario()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo agregar Región/Zona:\n{e}")

    def modificar_region_zona(self):
        if not self.region_zona_seleccionada_id:
            QMessageBox.warning(self, "Modificar", "Seleccione una región/zona para modificar.")
            return
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE regiones_zonas
                SET nombre_region_zona=%s, imagen_region_zona_ruta_relativa=%s, orden=%s
                WHERE id_region_zona=%s
            """, (
                self.lineEdit_nombre_region_zona.text(),
                self.lineEdit_ruta_imagen_region_zona.text(),
                self.spinBox_orden_region_zona.value(),
                self.region_zona_seleccionada_id
            ))
            conexion.commit()
            conexion.close()
            QMessageBox.information(self, "Región/Zona", "Región/Zona modificada correctamente.")
            self.cargar_regiones_zonas_activas()
            self.limpiar_formulario()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo modificar región/zona:\n{e}")

    def eliminar_region_zona(self):
        if not self.region_zona_seleccionada_id:
            QMessageBox.warning(self, "Error", "Debe seleccionar una región/zona para eliminar")
            return

        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("SELECT nombre_region_zona FROM regiones_zonas WHERE id_region_zona = %s", (self.region_zona_seleccionada_id,))
            region_zona = cursor.fetchone()
            if not region_zona:
                QMessageBox.warning(self, "Error", f"No se encontró ninguna región/zona con ID {self.region_zona_seleccionada_id}")
                return
            nombre_region_zona = region_zona[0]

            cursor.execute("SELECT nombre_sub_seccion FROM sub_secciones WHERE id_region_zona = %s", (self.region_zona_seleccionada_id,))
            subsecciones = cursor.fetchall()
            if subsecciones:
                lista_subs = "\n".join([s[0] for s in subsecciones])
                QMessageBox.information(
                    self, "Región con subsecciones",
                    f"La región/zona '{nombre_region_zona}' tiene subsecciones:\n\n{lista_subs}\n\nDebes reasignarlas o eliminarlas antes de borrar."
                )
                return

            confirmacion = QMessageBox.question(
                self, "Confirmar eliminación",
                f"¿Eliminar la región/zona '{nombre_region_zona}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirmacion != QMessageBox.Yes:
                return

            cursor.execute("DELETE FROM regiones_zonas WHERE id_region_zona=%s", (self.region_zona_seleccionada_id,))
            conexion.commit()
            QMessageBox.information(self, "Éxito", f"La región/zona '{nombre_region_zona}' fue eliminada.")
            self.cargar_regiones_zonas_activas()
            self.limpiar_formulario()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar la región/zona:\n{e}")
        finally:
            if cursor:
                cursor.close()
            if conexion:
                conexion.close()

    def desactivar_region_zona(self):
        if not self.region_zona_seleccionada_id:
            QMessageBox.warning(self, "Desactivar", "Seleccione una región para desactivar.")
            return
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("UPDATE regiones_zonas SET habilitar=0 WHERE id_region_zona=%s", (self.region_zona_seleccionada_id,))
            conexion.commit()
            conexion.close()
            QMessageBox.information(self, "Región/Zona", "Región/Zona desactivada.")
            self.cargar_regiones_zonas_activas()
            self.cargar_regiones_zonas_inactivas()
            self.limpiar_formulario()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo desactivar región/zona:\n{e}")     

    def reactivar_region_zona(self):
        if not self.region_zona_inactiva_id:
            QMessageBox.warning(self, "Reactivar", "Seleccione una región/zona inactiva.")
            return
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("UPDATE regiones_zonas SET habilitar=1 WHERE id_region_zona=%s", (self.region_zona_inactiva_id,))
            conexion.commit()
            conexion.close()
            QMessageBox.information(self, "Región/Zona", "Región/Zona reactivada.")
            self.cargar_regiones_zonas_activas()
            self.cargar_regiones_zonas_inactivas()
            self.region_zona_inactiva_id = None
            self.btnReactivarRegionZona.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo reactivar región/zona:\n{e}")

    def limpiar_formulario(self):
        self.lineEdit_nombre_region_zona.clear()
        self.lineEdit_ruta_imagen_region_zona.clear()
        self.spinBox_orden_region_zona.setValue(0)
        self.label_imagen_region_zona.setText("Sin icono")
        self.region_zona_seleccionada_id = None
        self.region_zona_inactiva_id = None
        self.btnAgregarRegionZona.setEnabled(True)
        self.btnModificarRegionZona.setEnabled(False)
        self.btnEliminarRegionZona.setEnabled(False)   # 🔹 estaba mal: al limpiar debe quedar deshabilitado
        self.btnDesactivarRegionZona.setEnabled(False)
        self.btnReactivarRegionZona.setEnabled(False)

    # ------------------ Imagenes -------------------

    def seleccionar_imagen_region_zona(self):
        ruta_origen, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen de Región/Zona", "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not ruta_origen:
            self.lineEdit_ruta_imagen_region_zona.clear()
            self.label_imagen_region_zona.setText("Sin icono")
            return

        carpeta_destino = os.path.join(os.getcwd(), "public", "assets", "imagenes", "regiones_zonas")
        os.makedirs(carpeta_destino, exist_ok=True)

        nombre_archivo = os.path.basename(ruta_origen)
        ruta_destino = os.path.join(carpeta_destino, nombre_archivo)

        try:
            # ✅ Verificamos si el archivo ya está en la carpeta destino
            if os.path.abspath(ruta_origen) == os.path.abspath(ruta_destino):
                ruta_final = ruta_destino  # ya está en la carpeta correcta, no copiamos nada
            else:
                # Si existe y es distinto → renombrar
                if os.path.exists(ruta_destino):
                    base, ext = os.path.splitext(nombre_archivo)
                    contador = 1
                    while True:
                        nuevo_nombre = f"{base}_{contador}{ext}"
                        nueva_ruta = os.path.join(carpeta_destino, nuevo_nombre)
                        if not os.path.exists(nueva_ruta):
                            ruta_destino = nueva_ruta
                            break
                        contador += 1
                shutil.copy(ruta_origen, ruta_destino)
                ruta_final = ruta_destino

        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo copiar la imagen:\n{e}")
            return

        ruta_relativa = f"/assets/imagenes/regiones_zonas/{os.path.basename(ruta_destino)}"
        self.lineEdit_ruta_imagen_region_zona.setText(ruta_relativa)

        pixmap_imagen = self.cargar_imagen_en_label(ruta_final, self.label_imagen_region_zona, size=75, circular=True)
        self.label_imagen_region_zona.setPixmap(pixmap_imagen)
        self.label_imagen_region_zona.setText("")


    def cargar_imagen_en_label(self, ruta_imagen, label=None, size=75, circular=True, center=True):
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
