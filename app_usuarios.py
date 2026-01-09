# -*- coding: utf-8 -*-
from PyQt5 import uic
from database_hosting import conectar_hosting as conectar_base_datos 
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QApplication, QMainWindow, QWidget, QMessageBox
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush, QPen, QColor, QPainterPath
from PyQt5.QtCore import Qt, QRectF
import os
import shutil
import hashlib
import requests
import time
from utils.image_utils import procesar_imagen

# -------------------------
# CACHE DE IMÁGENES PARA MEJORAR VELOCIDAD
# -------------------------
_image_cache = {}
_CACHE_MAX_SIZE = 100  # Máximo de imágenes en cache
_CACHE_TIMEOUT = 300   # 5 minutos en segundos

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

# -------------------------
# MÉTODOS DE BÚSQUEDA HÍBRIDA OPTIMIZADOS
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
        pass
    return ""

def verificar_url_remota(url: str) -> bool:
    """Verifica si una URL remota es accesible - OPTIMIZADA"""
    try:
        response = requests.head(url, timeout=3)  # Timeout más corto
        return response.status_code == 200
    except Exception:
        return False

def resolver_ruta_hibrida(ruta_absoluta_db: str, ruta_relativa_db: str) -> str:
    """
    Busca imágenes en REMOTO → LOCAL - OPTIMIZADA
    """
    # Limpiar cache antiguo periódicamente
    if len(_image_cache) > _CACHE_MAX_SIZE:
        limpiar_cache_antiguo()
    
    # 1. PRIMERO: Buscar en REMOTO usando ruta relativa
    if ruta_relativa_db:
        url_remota = obtener_url_remota(ruta_relativa_db)
        if url_remota and verificar_url_remota(url_remota):
            return url_remota
    
    # 2. SEGUNDO: Buscar en LOCAL con ruta absoluta
    if ruta_absoluta_db and os.path.exists(ruta_absoluta_db):
        return ruta_absoluta_db
    
    # 3. TERCERO: Buscar en estructura del proyecto
    if ruta_relativa_db:
        rutas_posibles = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                        "turismo-frontend", "public", ruta_relativa_db),
            os.path.join(os.getcwd(), "turismo-frontend", "public", ruta_relativa_db),
            ruta_absoluta_desde_relativa(ruta_relativa_db),
        ]
        
        for ruta in rutas_posibles:
            if ruta and os.path.exists(ruta):
                return ruta
    
    return ""

def cargar_imagen_desde_ruta(ruta_imagen: str, size: tuple = None):
    """
    Carga imagen desde URL remota o archivo local - CON CACHE
    """
    if not ruta_imagen:
        return None

    # Verificar cache primero
    cache_key = obtener_clave_cache(ruta_imagen, size)
    if cache_key in _image_cache:
        timestamp, pixmap = _image_cache[cache_key]
        if time.time() - timestamp < _CACHE_TIMEOUT:
            return pixmap
        else:
            del _image_cache[cache_key]

    try:
        # ✅ MANEJAR URL REMOTA (con timeout optimizado)
        if _is_url(ruta_imagen):
            response = requests.get(ruta_imagen, timeout=5)  # Timeout reducido
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                if not pixmap.isNull():
                    if size:
                        pixmap = pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    # Guardar en cache
                    _image_cache[cache_key] = (time.time(), pixmap)
                    return pixmap
            return None
        
        # ✅ MANEJAR ARCHIVO LOCAL
        elif os.path.exists(ruta_imagen):
            pixmap = QPixmap(ruta_imagen)
            if not pixmap.isNull():
                if size:
                    pixmap = pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
                # Guardar en cache
                _image_cache[cache_key] = (time.time(), pixmap)
                return pixmap
        
        return None
        
    except Exception as e:
        return None

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

def convertir_ruta_produccion(ruta_absoluta):
    """Convierte rutas absolutas a rutas relativas - VERSIÓN MEJORADA"""
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

        # ✅ OPTIMIZADO: Mostrar la foto usando sistema híbrido con cache
        ruta_foto = obtener_texto(fila, 10)
        self.cargar_foto_usuario_hibrida(ruta_foto)
            
    def convertir_ruta_windows_a_relativa(self, ruta_windows):
        """Convierte rutas absolutas de Windows a rutas relativas para producción"""
        if not ruta_windows:
            return ruta_windows
            
        # ✅ MEJORADO: Usar función unificada
        if ruta_windows.startswith(('E:/', 'C:/', 'D:/')) or os.path.isabs(ruta_windows):
            return convertir_ruta_produccion(ruta_windows)
        
        return ruta_windows

    def seleccionar_usuario_inactivo(self, fila, columna):
        item = self.tabla_usuarios_inactivos.item(fila, 0)
        if item:
            self.usuario_inactivo_id = item.text()
            self.btnReactivarUsuario.setEnabled(True)

            # ✅ OPTIMIZADO: Mostrar foto del usuario inactivo usando sistema híbrido con cache
            def obtener_texto_inactivo(f, c):
                item = self.tabla_usuarios_inactivos.item(f, c)
                return item.text() if item else ""

            ruta_foto = obtener_texto_inactivo(fila, 3)  # Asumiendo que la foto está en columna 3
            self.cargar_foto_usuario_hibrida(ruta_foto)

    def cargar_foto_usuario_hibrida(self, ruta_relativa):
        """Carga la foto del usuario usando sistema híbrido REMOTO → LOCAL - OPTIMIZADA"""
        if not ruta_relativa:
            self.mostrar_foto_placeholder("Sin foto")
            return

        try:
            # ✅ OPTIMIZADO: Usar sistema híbrido con cache
            ruta_encontrada = resolver_ruta_hibrida("", ruta_relativa)
            
            if ruta_encontrada:
                pixmap = cargar_imagen_desde_ruta(ruta_encontrada, (100, 100))
                if pixmap and not pixmap.isNull():
                    # Redondear la imagen
                    pixmap_redondeada = self.redondear_imagen_pixmap(pixmap, circular=True, size=100)
                    self.label_foto_usuario.setPixmap(pixmap_redondeada)
                    self.label_foto_usuario.setText("")
                    self.label_foto_usuario.setToolTip(f"Foto: {ruta_relativa}")
                else:
                    self.mostrar_foto_placeholder("Error cargando")
            else:
                self.mostrar_foto_placeholder("Foto no encontrada")
                
        except Exception as e:
            self.mostrar_foto_placeholder("Error")

    def mostrar_foto_placeholder(self, texto):
        """Muestra un placeholder cuando no hay foto"""
        self.label_foto_usuario.clear()
        self.label_foto_usuario.setText(texto)
        self.label_foto_usuario.setStyleSheet("""
            QLabel {
                background-color: #f7fafc; 
                color: #4a5568; 
                border: 2px dashed #cbd5e0;
                border-radius: 50px;
                font-weight: bold;
                font-size: 10px;
            }
        """)
        self.label_foto_usuario.setAlignment(Qt.AlignCenter)

    def redondear_imagen_pixmap(self, pixmap: QPixmap, circular=False, size=None):
        """Redondea un QPixmap ya cargado (para imágenes remotas y locales)"""
        if pixmap.isNull():
            return QPixmap()

        # Ajustar tamaño si se indicó
        if size:
            pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        if circular:
            # Crear máscara circular
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

        return pixmap

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
        try:
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
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudieron cargar los usuarios: {e}")

    def cargar_usuarios_inactivos(self):
        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT id_usuario, apellido_nombres_usuario, dni_usuario, email_usuario, foto_usuario
                FROM usuarios
                WHERE activo = 0
            """)
            resultados = cursor.fetchall()
            conexion.close()

            columnas = ["ID", "Nombre", "DNI", "Email", "Foto"]
            self.tabla_usuarios_inactivos.setColumnCount(len(columnas))
            self.tabla_usuarios_inactivos.setHorizontalHeaderLabels(columnas)
            self.tabla_usuarios_inactivos.setRowCount(0)

            for row_number, row_data in enumerate(resultados):
                self.tabla_usuarios_inactivos.insertRow(row_number)
                for column_number, data in enumerate(row_data):
                    item = QTableWidgetItem(str(data))
                    self.tabla_usuarios_inactivos.setItem(row_number, column_number, item)
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudieron cargar los usuarios inactivos: {e}")

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
                    nombre_usuario_acceso, password_usuario, foto_usuario, rol_usuario, activo
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
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

        # ✅ MEJORADO: Sanitizar ruta de foto usando función unificada
        ruta_foto = self.lineEdit_ruta_foto.text().strip()
        if ruta_foto and (ruta_foto.startswith(('E:/', 'C:/', 'D:/')) or os.path.isabs(ruta_foto)):
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
            try:
                conexion = conectar_base_datos()
                cursor = conexion.cursor()
                cursor.execute("UPDATE usuarios SET activo = 0 WHERE id_usuario = %s", (self.usuario_seleccionado_id,))
                conexion.commit()
                conexion.close()

                QMessageBox.information(self, "Usuario desactivado", "El usuario fue desactivado correctamente.")
                self.cargar_usuarios()
                self.cargar_usuarios_inactivos()
                self.limpiar_formulario()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo desactivar el usuario: {str(e)}")
            
    def seleccionar_foto_usuario(self):
        """Selecciona una foto, la convierte a WebP y la guarda correctamente"""

        archivo, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar foto de usuario (recomendado WebP)",
            "",
            "Imágenes WebP (*.webp);;"
            "Imágenes compatibles (*.webp *.jpg *.jpeg *.png *.bmp)"
        )

        if not archivo:
            self.lineEdit_ruta_foto.clear()
            self.mostrar_foto_placeholder("Sin foto")
            return

        # ==============================
        # 🔥 CONVERSIÓN AUTOMÁTICA A WEBP
        # ==============================
        try:
            archivo = convertir_a_webp(archivo)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo convertir la imagen a WebP:\n{e}")
            return

        # ==============================
        # 📁 CARPETA DESTINO (producción)
        # ==============================
        carpeta_destino = ruta_absoluta_desde_relativa("/assets/imagenes/fotos_usuarios")
        os.makedirs(carpeta_destino, exist_ok=True)

        nombre_archivo = os.path.basename(archivo)
        ruta_destino = os.path.join(carpeta_destino, nombre_archivo)

        # Evitar sobrescrituras
        contador = 1
        nombre_base, extension = os.path.splitext(nombre_archivo)
        while os.path.exists(ruta_destino):
            ruta_destino = os.path.join(
                carpeta_destino,
                f"{nombre_base}_{contador}{extension}"
            )
            contador += 1

        try:
            shutil.move(archivo, ruta_destino)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo guardar la imagen:\n{e}")
            return

        # ==============================
        # 🔗 RUTA RELATIVA PRODUCCIÓN
        # ==============================
        ruta_relativa = convertir_ruta_produccion(ruta_destino)
        self.lineEdit_ruta_foto.setText(ruta_relativa)

        # ==============================
        # 🖼 PREVIEW
        # ==============================
        pixmap = QPixmap(ruta_destino)
        if not pixmap.isNull():
            pixmap_redondeada = self.redondear_imagen_pixmap(
                pixmap,
                circular=True,
                size=100
            )
            self.label_foto_usuario.setPixmap(pixmap_redondeada)
            self.label_foto_usuario.setText("")
            self.label_foto_usuario.setToolTip(f"Foto: {ruta_relativa}")
        else:
            self.mostrar_foto_placeholder("Error cargando")

        # ==============================
        # 💾 ACTUALIZAR BD AUTOMÁTICO
        # ==============================
        if hasattr(self, 'usuario_seleccionado_id') and self.usuario_seleccionado_id:
            self.actualizar_foto_en_bd(ruta_relativa)


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
        except Exception as e:
            QMessageBox.warning(self, "Error BD", f"No se pudo actualizar la foto en la base de datos:\n{e}")

    def existe_foto_en_uso(self, ruta_foto, id_actual=None):
        """Verifica si una foto ya está siendo usada por otro usuario"""
        try:
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
        except Exception as e:
            return False

    def limpiar_formulario(self):
        """Limpia todos los campos del formulario"""
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

        self.mostrar_foto_placeholder("Sin foto")

        self.usuario_seleccionado_id = None
        self.usuario_inactivo_id = None
        
        self.btnAgregarUsuario.setEnabled(True)
        self.btnModificarUsuario.setEnabled(False)
        self.btnEliminarUsuario.setEnabled(False)
        self.btnReactivarUsuario.setEnabled(False)