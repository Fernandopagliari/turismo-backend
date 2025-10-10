# -*- coding: utf-8 -*-
from PyQt5 import uic
from database_hosting import conectar_hosting as conectar_base_datos 
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QApplication, QMainWindow, QWidget, QMessageBox
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush, QPen, QColor, QPainterPath
from PyQt5.QtCore import Qt
import os
import shutil
import hashlib

def ruta_absoluta_desde_relativa(relativa: str) -> str:
    """
    Convierte '/assets/...png' a la ruta absoluta correcta.
    """
    if not relativa:
        return ""

    # Subimos dos niveles desde src/backend a la raíz del proyecto
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    base_assets = os.path.join(base_dir, "public")

    # Quitamos el primer "/" o "\" si lo tiene
    ruta_limpia = relativa.lstrip("/\\")
    return os.path.normpath(os.path.join(base_assets, ruta_limpia))


class VentanaUsuarios(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlag(Qt.Window)
        self.resize(700, 550)
        self.centrar_ventana()
        self.parent_widget = parent
        
        # Ruta absoluta y robusta al archivo .ui
        ruta_ui = os.path.join(
            os.path.dirname(__file__),   # carpeta actual: src/backend
            "interfaz",                  # subcarpeta
            "usuarios.ui"                # archivo .ui
        )

        if not os.path.exists(ruta_ui):
            raise FileNotFoundError(f"No se encontró el archivo UI en: {ruta_ui}")

        uic.loadUi(ruta_ui, self)
        
        self.setWindowTitle("Gestión de Usuarios")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMinMaxButtonsHint)

        # Cargar usuarios
        self.cargar_usuarios()
        self.cargar_usuarios_inactivos()

        # Conectar botones
        self.btnAgregarUsuario.clicked.connect(self.agregar_usuario)
        self.btnModificarUsuario.clicked.connect(self.modificar_usuario)
        self.btnEliminarUsuario.clicked.connect(self.eliminar_usuario)
        self.btnLimpiarFormulario.clicked.connect(self.limpiar_formulario)
        self.btnFoto.clicked.connect(self.seleccionar_foto_usuario)
        self.btnCerrar.clicked.connect(self.close)

        self.tabla_usuarios_activos.setColumnWidth(0, 200)
        self.tabla_usuarios_activos.cellClicked.connect(self.seleccionar_usuario_tabla)
        self.tabla_usuarios_inactivos.cellClicked.connect(self.seleccionar_usuario_inactivo)
        self.btnReactivarUsuario.clicked.connect(self.reactivar_usuario)

    def centrar_ventana(self):
        pantalla = QApplication.primaryScreen().availableGeometry()
        ventana = self.frameGeometry()
        ventana.moveCenter(pantalla.center())
        self.move(ventana.topLeft())

    def closeEvent(self, event):
        if self.parent():
            self.parent().mostrar_menu_lateral()
        super().closeEvent(event)
        
    def seleccionar_usuario_tabla(self, fila, columna):
        def obtener_texto(f, c):
            item = self.tabla_usuarios_activos.item(f, c)
            return item.text() if item else ""

        # Guardamos el id (lo usás para modificar/eliminar)
        self.usuario_seleccionado_id = obtener_texto(fila, 0)

        # Campos del formulario
        self.lineEdit_apellido_nombre_usuario.setText(obtener_texto(fila, 1))
        self.lineEdit_dni_usuario.setText(obtener_texto(fila, 2))
        self.lineEdit_domicilio_usuario.setText(obtener_texto(fila, 3))
        self.comboBox_localidad_usuario.setCurrentText(obtener_texto(fila, 4))
        self.comboBox_provincia_usuario.setCurrentText(obtener_texto(fila, 5))
        self.lineEdit_telefono_usuario.setText(obtener_texto(fila, 6))
        self.lineEdit_email_usuario.setText(obtener_texto(fila, 7))
        self.lineEdit_usuario_acceso.setText(obtener_texto(fila, 8))
        self.lineEdit_password_usuario.setText(obtener_texto(fila, 9))
        self.lineEdit_ruta_foto.setText(obtener_texto(fila, 10))
        self.comboBox_rol_usuario.setCurrentText(obtener_texto(fila, 11))

        # Botones
        self.btnAgregarUsuario.setEnabled(False)
        self.btnModificarUsuario.setEnabled(True)
        self.btnEliminarUsuario.setEnabled(True)

        # Mostrar la foto usando ruta_absoluta_desde_relativa
        ruta_foto = obtener_texto(fila, 10)
        if ruta_foto:
            ruta_absoluta = ruta_absoluta_desde_relativa(ruta_foto)
            if os.path.exists(ruta_absoluta):
                self.label_foto_usuario.setText("")
                self.redondear_imagen(
                    ruta_absoluta,
                    self.label_foto_usuario,
                    circular=True,
                    size=100
                )
            else:
                self.label_foto_usuario.clear()
                self.label_foto_usuario.setText("Sin foto")
        else:
            self.label_foto_usuario.clear()
            self.label_foto_usuario.setText("Sin foto")
            
    def convertir_ruta_windows_a_relativa(self, ruta_windows):
        """Convierte rutas absolutas de Windows a rutas relativas para producción"""
        if not ruta_windows or not ruta_windows.startswith('E:/'):
            return ruta_windows
        
        # Extraer solo el nombre del archivo y construir ruta relativa
        nombre_archivo = os.path.basename(ruta_windows)
        return f"/assets/imagenes/fotos_usuarios/{nombre_archivo}"

    def seleccionar_usuario_inactivo(self, fila, columna):
        item = self.tabla_usuarios_inactivos.item(fila, 0)
        if item:
            self.usuario_inactivo_id = item.text()
            self.btnReactivarUsuario.setEnabled(True)

            # Mostrar foto del usuario inactivo
            def obtener_texto_inactivo(f, c):
                item = self.tabla_usuarios_inactivos.item(f, c)
                return item.text() if item else ""

            ruta_foto = obtener_texto_inactivo(fila, 10)
            if ruta_foto:
                ruta_absoluta = ruta_absoluta_desde_relativa(ruta_foto)
                if os.path.exists(ruta_absoluta):
                    self.label_foto_usuario.setText("")
                    self.redondear_imagen(
                        ruta_absoluta,
                        self.label_foto_usuario,
                        circular=True,
                        size=100
                    )
                else:
                    self.label_foto_usuario.clear()
                    self.label_foto_usuario.setText("Sin foto")
            else:
                self.label_foto_usuario.clear()
                self.label_foto_usuario.setText("Sin foto")

    def reactivar_usuario(self):
        if not hasattr(self, 'usuario_inactivo_id') or not self.usuario_inactivo_id:
            QMessageBox.warning(self, "Seleccionar", "Seleccioná un usuario para reactivar.")
            return

        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute(
                "UPDATE usuarios SET activo = 1 WHERE id_usuario = %s",
                (self.usuario_inactivo_id,)
            )
            conexion.commit()
            cursor.close()
            conexion.close()

            QMessageBox.information(self, "Usuario reactivado", "El usuario fue reactivado correctamente.")
            self.cargar_usuarios()
            self.cargar_usuarios_inactivos()
            self.btnReactivarUsuario.setEnabled(False)
            self.usuario_inactivo_id = None

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo reactivar el usuario:\n{e}")

    def cargar_usuarios(self):
        conexion = conectar_base_datos()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT id_usuario, apellido_nombres_usuario, dni_usuario, domicilio_usuario,
                   localidad_usuario, provincia_usuario, telefono_usuario, email_usuario,
                   nombre_usuario_acceso, password_usuario, foto_usuario, rol_usuario
            FROM usuarios
            WHERE activo = 1
        """)
        resultados = cursor.fetchall()
        conexion.close()

        columnas = [
            "ID", "Nombre", "DNI", "Domicilio", "Localidad", "Provincia",
            "Teléfono", "Email", "Usuario", "Contraseña", "Foto", "Rol"
        ]
        self.tabla_usuarios_activos.setColumnCount(len(columnas))
        self.tabla_usuarios_activos.setHorizontalHeaderLabels(columnas)
        self.tabla_usuarios_activos.setRowCount(0)

        for row_number, row_data in enumerate(resultados):
            self.tabla_usuarios_activos.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                item = QTableWidgetItem(str(data))
                self.tabla_usuarios_activos.setItem(row_number, column_number, item)

    def cargar_usuarios_inactivos(self):
        conexion = conectar_base_datos()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT id_usuario, apellido_nombres_usuario, dni_usuario, email_usuario
            FROM usuarios
            WHERE activo = 0
        """)
        resultados = cursor.fetchall()
        conexion.close()

        columnas = ["ID", "Nombre", "DNI", "Email"]
        self.tabla_usuarios_inactivos.setColumnCount(len(columnas))
        self.tabla_usuarios_inactivos.setHorizontalHeaderLabels(columnas)
        self.tabla_usuarios_inactivos.setRowCount(0)

        for row_number, row_data in enumerate(resultados):
            self.tabla_usuarios_inactivos.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                item = QTableWidgetItem(str(data))
                self.tabla_usuarios_inactivos.setItem(row_number, column_number, item)

    def agregar_usuario(self):
        apellido_nombre = self.lineEdit_apellido_nombre_usuario.text().strip()
        dni = self.lineEdit_dni_usuario.text().strip()
        domicilio = self.lineEdit_domicilio_usuario.text().strip()
        localidad = self.comboBox_localidad_usuario.currentText().strip()
        provincia = self.comboBox_provincia_usuario.currentText().strip()
        telefono = self.lineEdit_telefono_usuario.text().strip()
        email = self.lineEdit_email_usuario.text().strip()
        usuario_acceso = self.lineEdit_usuario_acceso.text().strip()
        password = self.lineEdit_password_usuario.text().strip()
        ruta_foto = self.lineEdit_ruta_foto.text().strip()
        rol = self.comboBox_rol_usuario.currentText().strip()

        if not apellido_nombre or not dni or not usuario_acceso or not password:
            QMessageBox.warning(self, "Campos obligatorios", "Debe completar al menos: nombre, DNI, usuario y contraseña.")
            return

        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                INSERT INTO usuarios (
                    apellido_nombres_usuario, dni_usuario, domicilio_usuario,
                    localidad_usuario, provincia_usuario, telefono_usuario, email_usuario,
                    nombre_usuario_acceso, password_usuario, foto_usuario, rol_usuario
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (apellido_nombre, dni, domicilio, localidad, provincia, telefono, email,
                  usuario_acceso, password, ruta_foto, rol))
            conexion.commit()
            conexion.close()

            QMessageBox.information(self, "Usuario agregado", "El usuario fue agregado correctamente.")
            self.cargar_usuarios()
            self.limpiar_formulario()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo agregar el usuario.\n{str(e)}")

    def modificar_usuario(self):
        if not hasattr(self, 'usuario_seleccionado_id') or not self.usuario_seleccionado_id:
            QMessageBox.warning(self, "Modificación", "Seleccione un usuario de la tabla para modificar.")
            return

        # ✅ CORREGIDO: Sanitizar ruta de foto antes de guardar
        ruta_foto = self.lineEdit_ruta_foto.text().strip()
        if ruta_foto and ruta_foto.startswith('E:/'):
            # Convertir ruta absoluta de Windows a relativa
            ruta_foto = self.convertir_ruta_windows_a_relativa(ruta_foto)

        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE usuarios
                SET apellido_nombres_usuario = %s, dni_usuario = %s, domicilio_usuario = %s,
                    localidad_usuario = %s, provincia_usuario = %s, telefono_usuario = %s,
                    email_usuario = %s, nombre_usuario_acceso = %s, password_usuario = %s,
                    foto_usuario = %s, rol_usuario = %s
                WHERE id_usuario = %s
            """, (
                self.lineEdit_apellido_nombre_usuario.text(),
                self.lineEdit_dni_usuario.text(),
                self.lineEdit_domicilio_usuario.text(),
                self.comboBox_localidad_usuario.currentText(),
                self.comboBox_provincia_usuario.currentText(),
                self.lineEdit_telefono_usuario.text(),
                self.lineEdit_email_usuario.text(),
                self.lineEdit_usuario_acceso.text(),
                self.lineEdit_password_usuario.text(),
                ruta_foto,  # ✅ Usar ruta sanitizada
                self.comboBox_rol_usuario.currentText(),
                self.usuario_seleccionado_id
            ))
            conexion.commit()
            QMessageBox.information(self, "Modificación exitosa", "Usuario modificado correctamente.")
            self.cargar_usuarios()
            self.limpiar_formulario()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error al modificar el usuario:\n{str(e)}")
        finally:
            conexion.close()
    def eliminar_usuario(self):
        if not self.usuario_seleccionado_id:
            QMessageBox.warning(self, "Selección requerida", "Por favor seleccione un usuario.")
            return

        respuesta = QMessageBox.question(
            self, "Confirmar Desactivación",
            "¿Está seguro que desea desactivar este usuario?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if respuesta == QMessageBox.Yes:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("UPDATE usuarios SET activo = 0 WHERE id_usuario = %s", (self.usuario_seleccionado_id,))
            conexion.commit()
            conexion.close()

            QMessageBox.information(self, "Usuario desactivado", "El usuario fue desactivado correctamente.")
            self.cargar_usuarios()
            self.cargar_usuarios_inactivos()
            self.limpiar_formulario()
            
    def seleccionar_foto_usuario(self):
        ruta_origen, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar foto de usuario", "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif)"
        )

        if not ruta_origen:
            self.lineEdit_ruta_foto.clear()
            self.label_foto_usuario.clear()
            self.label_foto_usuario.setText("Sin foto")
            return

        # ✅ CORREGIDO: Carpeta destino usando ruta absoluta
        carpeta_destino = ruta_absoluta_desde_relativa("/assets/imagenes/fotos_usuarios")
        
        # Asegurar que la carpeta existe
        os.makedirs(carpeta_destino, exist_ok=True)

        nombre_archivo = os.path.basename(ruta_origen)
        nombre_base, extension = os.path.splitext(nombre_archivo)
        ruta_destino = os.path.join(carpeta_destino, nombre_archivo)

        try:
            if os.path.exists(ruta_destino) and os.path.samefile(ruta_origen, ruta_destino):
                # Ya está en la carpeta destino → no copiamos
                ruta_final = ruta_destino
            else:
                # Si ya existe pero es diferente, renombramos con sufijo _1, _2...
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
            QMessageBox.warning(self, "Error", f"No se pudo copiar la foto:\n{e}")
            return

        # ✅ CORREGIDO: Guardamos SOLO la ruta relativa
        ruta_relativa = f"/assets/imagenes/fotos_usuarios/{os.path.basename(ruta_destino)}"

        # ✅ CORREGIDO: Forzar que solo se guarde la ruta relativa
        self.lineEdit_ruta_foto.setText(ruta_relativa)
        
        # Mostrar imagen
        pixmap_foto = self.redondear_imagen(ruta_final, self.label_foto_usuario, circular=True, size=100)
        self.label_foto_usuario.setPixmap(pixmap_foto)
        self.label_foto_usuario.setText("")

        # ✅ CORREGIDO: Actualizar automáticamente en BD si hay usuario seleccionado
        if hasattr(self, 'usuario_seleccionado_id') and self.usuario_seleccionado_id:
            self.actualizar_foto_en_bd(ruta_relativa)
    def redondear_imagen(self, ruta_imagen, label, circular=False, size=None):
        from PyQt5.QtGui import QPixmap, QPainter, QPainterPath
        from PyQt5.QtCore import Qt, QRectF

        pixmap = QPixmap(ruta_imagen)

        # Ajustar tamaño si se indicó
        if size:
            pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        if circular:
            # Hacer circular la imagen
            mask = QPixmap(pixmap.size())
            mask.fill(Qt.transparent)

            painter = QPainter(mask)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addEllipse(QRectF(0, 0, pixmap.width(), pixmap.height()))
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()

            pixmap = mask

        # Mostrar en el QLabel
        label.setPixmap(pixmap)
        label.setScaledContents(True)

        return pixmap
    
    def actualizar_foto_en_bd(self, ruta_relativa):
        """Actualiza automáticamente la foto en la base de datos"""
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE usuarios
                SET foto_usuario = %s
                WHERE id_usuario = %s
            """, (ruta_relativa, self.usuario_seleccionado_id))
            conexion.commit()
            conexion.close()
            print(f"✅ Foto actualizada en BD: {ruta_relativa}")
        except Exception as e:
            print(f"❌ Error actualizando foto en BD: {e}")

    def existe_foto_en_uso(self, ruta_foto, id_actual=None):
        conexion = conectar_base_datos()
        cursor = conexion.cursor()
        if id_actual:
            cursor.execute("""
                SELECT COUNT(*) FROM usuarios
                WHERE foto_usuario = %s AND id_usuario != %s
            """, (ruta_foto, id_actual))
        else:
            cursor.execute("SELECT COUNT(*) FROM usuarios WHERE foto_usuario = %s", (ruta_foto,))
        resultado = cursor.fetchone()[0]
        conexion.close()
        return resultado > 0

    def limpiar_formulario(self):
        self.lineEdit_apellido_nombre_usuario.clear()
        self.lineEdit_dni_usuario.clear()
        self.lineEdit_domicilio_usuario.clear()
        self.lineEdit_email_usuario.clear()
        self.lineEdit_telefono_usuario.clear()
        self.lineEdit_usuario_acceso.clear()
        self.lineEdit_password_usuario.clear()
        self.lineEdit_ruta_foto.clear()

        self.comboBox_localidad_usuario.setCurrentIndex(0)
        self.comboBox_provincia_usuario.setCurrentIndex(0)
        self.comboBox_rol_usuario.setCurrentIndex(0)

        self.label_foto_usuario.clear()
        self.label_foto_usuario.setText("Sin foto")

        self.usuario_seleccionado_id = None
        
        self.btnAgregarUsuario.setEnabled(True)
        self.btnModificarUsuario.setEnabled(False)
        self.btnEliminarUsuario.setEnabled(False)