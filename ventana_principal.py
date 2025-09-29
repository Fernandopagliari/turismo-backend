# ventana_principal.py
import os
import sys
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox
from PyQt5 import uic
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QSize

from database import conectar_base_datos
from app_usuarios import VentanaUsuarios
from app_secciones import VentanaSecciones
from app_sub_secciones import VentanaSubSecciones
from app_configuracion import VentanaConfiguracion
from app_regiones_zonas import VentanaRegionesZonas


class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()

        # Ruta absoluta y robusta al archivo .ui
        ruta_ui = os.path.join(
            os.path.dirname(__file__),
            "interfaz",
            "ventana_principal.ui"
        )
        if not os.path.exists(ruta_ui):
            raise FileNotFoundError(f"No se encontró el archivo UI en: {ruta_ui}")

        uic.loadUi(ruta_ui, self)

        # Inicializo variable para configuración
        self.config = None
        self.menu_icon_path = None
        self.close_icon_path = None

        # Mover el menú lateral fuera de pantalla inicialmente
        try:
            self.frame_menu_lateral.move(-self.frame_menu_lateral.width(), self.btnMenu.height())
        except Exception:
            pass

        # Maximizar ventana
        self.showMaximized()

        # Cargar configuración (iconos, hero) desde la BD
        self.cargar_configuracion()

        # Configurar interfaz (con iconos según BD o fallback)
        self.configurar_interfaz()

        # Cargar imagen central (hero)
        self.cargar_imagen_central()
        
        
    def ruta_absoluta_desde_relativa(self, relativa: str) -> str:
        """
        Convierte rutas relativas tipo '/assets/...' a ruta absoluta dentro del proyecto.
        """
        if not relativa:
            return ""
        
        # Subimos dos niveles desde src/backend a la raíz del proyecto
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        base_assets = os.path.join(base_dir, "public")  # carpeta public donde están los assets
        
        # Limpiamos la ruta relativa de posibles "/" o "\"
        ruta_limpia = relativa.lstrip("/\\")
        
        return os.path.normpath(os.path.join(base_assets, ruta_limpia))

    # -------------------------
    # Helpers: resolver rutas
    # -------------------------
    def _is_url(self, path):
        return isinstance(path, str) and (path.startswith("http://") or path.startswith("https://"))

    def _normalize_db_path(self, ruta):
        """
        Normaliza una ruta proveniente de la BD para facilitar búsquedas:
         - quita barras iniciales
         - transforma 'public/assets/...' o '/assets/...' a 'assets/...'
         - reemplaza backslashes por slashes
        """
        if not ruta or not isinstance(ruta, str):
            return ruta
        r = ruta.replace("\\", "/").strip()
        # quitar barra inicial
        r = r.lstrip("/")
        # si viene con 'public/' dejamos solo lo que viene después
        if r.startswith("public/"):
            r = r.replace("public/", "", 1)
        return r

    def _search_for_filename_in_project(self, filename, project_root, max_matches=20):
        """
        Busca el filename dentro de project_root (recorrido limitado).
        Devuelve lista de coincidencias (rutas absolutas), hasta max_matches.
        Esto ayuda a localizar dónde está realmente el archivo si las candidatas fallan.
        """
        matches = []
        # Buscamos por basename (por si BD guarda sólo /assets/imagenes/archivo.jpg)
        basename = os.path.basename(filename)
        try:
            for root, dirs, files in os.walk(project_root):
                if basename in files:
                    matches.append(os.path.join(root, basename))
                    if len(matches) >= max_matches:
                        break
            return matches
        except Exception as e:
            print(f"[search] Error buscando {basename} en {project_root}: {e}")
            return matches

    def resolve_asset_path(self, ruta):
        """
        Devuelve la primera ruta absoluta existente para la ruta 'ruta' guardada en BD.
        Si 'ruta' es URL, devuelve la URL (pero NOTA: QPixmap/QIcon no cargan http directamente).
        Si no encuentra nada, devuelve None.

        Imprime por consola las candidatas y cuál existe (diagnóstico ampliado).
        """
        if not ruta:
            return None

        ruta_raw = ruta
        ruta = ruta.replace("\\", "/").strip()

        # si es URL HTTP/HTTPS devolvemos tal cual (no se descarga automáticamente)
        if self._is_url(ruta):
            print(f"[resolve_asset_path] Ruta es URL: {ruta} (no se descarga automáticamente)")
            return ruta

        # si es path absoluto en Windows ó Unix y existe, lo devolvemos
        if os.path.isabs(ruta) and os.path.exists(ruta):
            p = os.path.normpath(ruta)
            print(f"[resolve_asset_path] Ruta absoluta encontrada: {p}")
            return p

        # paths del proyecto
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        # intento definir project_root asumiendo estructura repo: backend/... => project_root = dos niveles arriba
        project_root = os.path.abspath(os.path.join(backend_dir, "..", ".."))

        # Normalizar lo que vino de la BD para mapear '/assets/...' a frontend/public/assets/...
        cleaned = self._normalize_db_path(ruta)

        candidates = []

        # Varios lugares habituales donde el material puede estar
        # 1) frontend/public/<cleaned>
        candidates.append(os.path.join(project_root, "frontend", "public", cleaned))
        # 2) frontend/src/assets/<cleaned> (común en proyectos Vue/React)
        candidates.append(os.path.join(project_root, "frontend", "src", cleaned))
        candidates.append(os.path.join(project_root, "frontend", "src", "assets", cleaned))
        # 3) frontend/assets/<cleaned>
        candidates.append(os.path.join(project_root, "frontend", "assets", cleaned))
        # 4) frontend/dist/assets/<cleaned> / frontend/build/assets
        candidates.append(os.path.join(project_root, "frontend", "dist", "assets", cleaned))
        candidates.append(os.path.join(project_root, "frontend", "build", "assets", cleaned))
        # 5) project_root/<cleaned>
        candidates.append(os.path.join(project_root, cleaned))
        # 6) project_root/assets/<cleaned> and project_root/static
        candidates.append(os.path.join(project_root, "assets", cleaned))
        candidates.append(os.path.join(project_root, "static", cleaned))
        # 7) backend_dir/<cleaned>
        candidates.append(os.path.join(backend_dir, cleaned))
        # 8) normalizar ruta original bajo project_root y backend_dir (por si BD guardó rutas relativas distintas)
        candidates.append(os.path.normpath(os.path.join(project_root, ruta_raw)))
        candidates.append(os.path.normpath(os.path.join(backend_dir, ruta_raw)))
        # 9) cwd
        candidates.append(os.path.normpath(os.path.join(os.getcwd(), cleaned)))

        # Mostrar lo que intentamos
        print("[resolve_asset_path] Ruta solicitada:", ruta_raw)
        print("[resolve_asset_path] Candidatas (en este orden):")
        for c in candidates:
            try:
                print("   -", c, " -> exists:", os.path.exists(c))
            except Exception:
                print("   -", c, " -> exists: (error comprobando)")

        # Devolver la primera que exista
        for p in candidates:
            try:
                if p and os.path.exists(p):
                    pnorm = os.path.normpath(p)
                    print(f"[resolve_asset_path] Usando: {pnorm}")
                    return pnorm
            except Exception:
                pass

        # Si no encontramos nada, intentamos buscar el nombre del archivo en el project_root para dar pista al dev
        basename = os.path.basename(cleaned)
        print(f"[resolve_asset_path] No se encontró archivo en candidatas. Buscando '{basename}' dentro de {project_root} (esto puede tardar unos segundos)...")
        matches = self._search_for_filename_in_project(basename, project_root, max_matches=20)
        if matches:
            print("[resolve_asset_path] Se encontraron coincidencias en el repo (posibles ubicaciones del archivo):")
            for m in matches:
                print("   -", m)
        else:
            print("[resolve_asset_path] No se encontró ninguna coincidencia del nombre de archivo en el repo.")

        print("[resolve_asset_path] No se encontró archivo en ninguna candidata.")
        return None

    def find_asset_or_fallback(self, ruta_bd, fallback_relative):
        """
        Intenta resolver ruta desde BD. Si no existe, intenta fallback_relative relativo al project_root/frontend/public.
        Devuelve una ruta absoluta existente o None.
        """
        # 1) intentar BD
        if ruta_bd:
            ruta_res = self.resolve_asset_path(ruta_bd)
            
            if ruta_res:
                # si es URL, devolvemos la URL (pero avisamos)
                if self._is_url(ruta_res):
                    print(f"[find_asset_or_fallback] Ruta BD es URL: {ruta_res}")
                    return ruta_res
                if os.path.exists(ruta_res):
                    print(f"[find_asset_or_fallback] Ruta BD válida: {ruta_res}")
                    return ruta_res
                else:
                    print(f"[find_asset_or_fallback] La ruta resuelta desde BD no existe en disco: {ruta_res}")
            
        # 2) fallback en frontend/public/<fallback_relative>
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(backend_dir, "..", ".."))
        fallback_clean = fallback_relative.lstrip("./").lstrip("/")
        fallback_abs = os.path.join(project_root, "frontend", "public", fallback_clean)
        print(f"[find_asset_or_fallback] Intentando fallback: {fallback_abs} (exists: {os.path.exists(fallback_abs)})")
        if os.path.exists(fallback_abs):
            return os.path.normpath(fallback_abs)

        # 3) intentar fallback relativo al backend
        fallback_backend = os.path.join(backend_dir, fallback_clean)
        print(f"[find_asset_or_fallback] Intentando fallback backend: {fallback_backend} (exists: {os.path.exists(fallback_backend)})")
        if os.path.exists(fallback_backend):
            return os.path.normpath(fallback_backend)

        # 4) intentar fallback en cwd
        fallback_cwd = os.path.normpath(os.path.join(os.getcwd(), fallback_clean))
        print(f"[find_asset_or_fallback] Intentando fallback cwd: {fallback_cwd} (exists: {os.path.exists(fallback_cwd)})")
        if os.path.exists(fallback_cwd):
            return fallback_cwd

        print("[find_asset_or_fallback] No se encontró ni BD ni fallback.")
        return None

    # -------------------------
    # Cargar configuración BD
    # -------------------------
    def cargar_configuracion(self):
        try:
            conn = conectar_base_datos()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id_config, titulo_app, logo_app, icono_hamburguesa, icono_cerrar, 
                       hero_titulo, hero_imagen, footer_texto 
                FROM configuracion_app 
                WHERE habilitar=1 LIMIT 1
            """)
            fila = cursor.fetchone()
            cursor.close()
            conn.close()
            if fila:
                self.config = fila
                print("[CONFIG] Configuración cargada desde BD:", fila)
            else:
                self.config = None
        except Exception as e:
            print("Error cargando configuración desde BD:", e)
            self.config = None

    # -------------------------
    # Interfaz / iconos navbar
    # -------------------------
    def configurar_interfaz(self):
        icono_menu_bd = None
        icono_cerrar_bd = None
        if self.config:
            icono_menu_bd = self.config.get("icono_hamburguesa")
            icono_cerrar_bd = self.config.get("icono_cerrar")

        # Intentar cargar desde BD, si no usar fallback dentro del repo
        self.menu_icon_path = self.find_asset_or_fallback(icono_menu_bd, "assets/iconos/menu.png")
        self.close_icon_path = self.find_asset_or_fallback(icono_cerrar_bd, "assets/iconos/cerrar.png")

        print(f"[ICONOS] Hamburguesa → {self.menu_icon_path}")
        print(f"[ICONOS] Cerrar → {self.close_icon_path}")

        try:
            # Si la ruta es una URL (http/https) no intentamos usar QIcon con la URL
            if self.menu_icon_path and not self._is_url(self.menu_icon_path) and os.path.exists(self.menu_icon_path):
                self.btnMenu.setIcon(QIcon(self.menu_icon_path))
            else:
                # intentar si es URL (indicamos en consola) o dejar sin icono
                if self.menu_icon_path and self._is_url(self.menu_icon_path):
                    print("[configurar_interfaz] Atención: icono menú es URL. QIcon no carga URLs directamente.")
                self.btnMenu.setIcon(QIcon())
            self.btnMenu.setIconSize(QSize(40, 40))
        except Exception as e:
            print("Error asignando icono menú:", e)

        try:
            self.btnConfiguracion.setVisible(False)
            self.btnUsuarios.setVisible(False)
            self.btnRegionesZonas.setVisible(False)            
            self.btnSecciones.setVisible(False)
            self.btnSubSecciones.setVisible(False)
            self.btnGestionCargas.setVisible(False)
        except Exception:
            pass

        try:
            self.btnMenu.clicked.connect(self.alternar_menu_lateral)
            self.btnLoginAceptar.clicked.connect(self.iniciar_sesion)
            self.btnCerrarSesion.clicked.connect(self.cerrar_sesion)
            self.btnSalir.clicked.connect(self.close)
            self.btnGestionCargas.clicked.connect(self.alternar_submenu_datos)

            self.btnUsuarios.clicked.connect(self.abrir_gestion_usuarios)
            self.btnRegionesZonas.clicked.connect(self.abrir_gestion_regionesZonas)
            self.btnSecciones.clicked.connect(self.abrir_gestion_secciones)
            self.btnSubSecciones.clicked.connect(self.abrir_gestion_sub_secciones)
            self.btnConfiguracion.clicked.connect(self.abrir_gestion_configuracion)
        except Exception as e:
            print("Error conectando botones:", e)

        self.usuario_actual = None
        try:
            self.label_estado_login.setText("No hay sesión iniciada.")
        except Exception:
            pass
        self.bloquear_funcionalidades()

    # -------------------------
    # Imagen central (hero)
    # -------------------------
    def cargar_imagen_central(self):
        """
        Carga la imagen hero desde la configuración guardada en BD.
        Usa fallback si la ruta de la BD no existe.
        """
        try:
            ruta_relativa = None
            if self.config and self.config.get("hero_imagen"):
                ruta_relativa = self.config.get("hero_imagen")
            else:
                conn = conectar_base_datos()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT hero_imagen FROM configuracion_app WHERE habilitar=1 LIMIT 1")
                res = cursor.fetchone()
                cursor.close()
                conn.close()
                if res:
                    ruta_relativa = res.get("hero_imagen")

            if not ruta_relativa:
                print("No hay imagen configurada en la base de datos")
                self.mostrar_imagen_alternativa()
                return

            ruta_resuelta = self.find_asset_or_fallback(ruta_relativa, "assets/imagenes/hongo_ischigualasto.jpg")
            print(f"[HERO] Intentando cargar imagen central desde: {ruta_resuelta}")

            if ruta_resuelta:
                if self._is_url(ruta_resuelta):
                    print("[HERO] Atención: hero_imagen es una URL. QPixmap no cargará sin descarga.")
                    self.mostrar_imagen_alternativa()
                    return

                if os.path.exists(ruta_resuelta):
                    pixmap = QPixmap(ruta_resuelta)
                    if not pixmap.isNull() and hasattr(self, "label_imagen_central"):
                        scaled_pixmap = pixmap.scaled(
                            self.label_imagen_central.size(),
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation
                        )
                        self.label_imagen_central.setPixmap(scaled_pixmap)
                        self.label_imagen_central.setAlignment(Qt.AlignCenter)
                        self.label_imagen_central.setStyleSheet("")
                    else:
                        print("Error: la imagen no se pudo cargar (pixmap inválido).")
                        self.mostrar_imagen_alternativa()
                else:
                    print(f"Error: No existe la ruta: {ruta_resuelta}")
                    self.mostrar_imagen_alternativa()
            else:
                print("[HERO] No se resolvió ninguna ruta válida para hero.")
                self.mostrar_imagen_alternativa()
        except Exception as e:
            print(f"Error al cargar imagen central: {e}")
            self.mostrar_imagen_alternativa()

    def mostrar_imagen_alternativa(self):
        if hasattr(self, "label_imagen_central"):
            self.label_imagen_central.setText("Imagen no disponible")
            self.label_imagen_central.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    color: #666;
                    qproperty-alignment: AlignCenter;
                }
            """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.ajustar_imagen()

    def ajustar_imagen(self):
        try:
            if hasattr(self, 'label_imagen_central') and self.label_imagen_central.pixmap():
                pixmap = self.label_imagen_central.pixmap()
                if pixmap:
                    scaled = pixmap.scaled(
                        self.label_imagen_central.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.label_imagen_central.setPixmap(scaled)
        except Exception:
            pass

    # -------------------------
    # Drawer (menu lateral)
    # -------------------------
    def mostrar_menu_lateral(self):
        self.animar_drawer(mostrar=True)
        if self.close_icon_path and os.path.exists(self.close_icon_path):
            self.btnMenu.setIcon(QIcon(self.close_icon_path))
        self.btnMenu.setIconSize(QSize(40, 40))

    def alternar_menu_lateral(self):
        esta_oculto = self.frame_menu_lateral.x() < 0
        self.animar_drawer(esta_oculto)
        icono = self.close_icon_path if esta_oculto else self.menu_icon_path
        if icono and os.path.exists(icono):
            self.btnMenu.setIcon(QIcon(icono))
        else:
            self.btnMenu.setIcon(QIcon())
        self.btnMenu.setIconSize(QSize(40, 40))

    def animar_drawer(self, mostrar=True):
        ancho = self.frame_menu_lateral.width()
        x_origen = self.frame_menu_lateral.x()
        x_destino = 0 if mostrar else -ancho
        y_fijo = self.btnMenu.height() if hasattr(self, "btnMenu") else 0

        animacion = QPropertyAnimation(self.frame_menu_lateral, b"pos")
        animacion.setDuration(300)
        animacion.setStartValue(QPoint(x_origen, y_fijo))
        animacion.setEndValue(QPoint(x_destino, y_fijo))
        animacion.setEasingCurve(QEasingCurve.InOutQuart)
        animacion.start()
        self.animacion_drawer = animacion

    # -------------------------
    # Login / sesión
    # -------------------------
    def iniciar_sesion(self):
        usuario = getattr(self, "lineEdit_usuario", None).text() if hasattr(self, "lineEdit_usuario") else ""
        clave = getattr(self, "lineEdit_password", None).text() if hasattr(self, "lineEdit_password") else ""

        if not usuario or not clave:
            QMessageBox.warning(self, "Campos Vacíos", "Por favor ingrese usuario y contraseña.")
            return

        try:
            conexion = conectar_base_datos()
            cursor = conexion.cursor(dictionary=True)
            cursor.execute("""
                SELECT id_usuario, apellido_nombres_usuario, rol_usuario, foto_usuario, password_usuario, activo
                FROM usuarios
                WHERE nombre_usuario_acceso = %s
            """, (usuario,))
            resultado = cursor.fetchone()
            cursor.close()
            conexion.close()
        except Exception as e:
            QMessageBox.critical(self, "Error BD", f"No se pudo consultar usuarios:\n{e}")
            return

        if resultado:
            nombre_completo = resultado.get("apellido_nombres_usuario")
            rol = resultado.get("rol_usuario")
            ruta_foto = resultado.get("foto_usuario")
            password_guardada = resultado.get("password_usuario")
            activo = resultado.get("activo")

            if not activo:
                QMessageBox.critical(self, "Usuario inactivo", "Este usuario está inactivo y no puede iniciar sesión.")
                try:
                    self.label_estado_login.setText("Usuario inactivo.")
                    self.label_estado_login.setStyleSheet("color: red;")
                except Exception:
                    pass
                return

            if clave == password_guardada:
                self.usuario_actual = nombre_completo
                self.rol_usuario_actual = rol
                try:
                    self.label_estado_login.setText(f"Sesión activa: {self.usuario_actual} ({self.rol_usuario_actual})")
                    self.label_estado_login.setStyleSheet("color: black;")
                except Exception:
                    pass
                QMessageBox.information(self, "Bienvenido", f"Bienvenido {self.usuario_actual}")

                # Mostrar foto de usuario (resolver ruta)
                self.mostrar_foto_usuario_en_label(ruta_foto, self.label_foto_usuario, size=100)


                # Bloquear inputs
                try:
                    self.lineEdit_usuario.setEnabled(False)
                    self.lineEdit_password.setEnabled(False)
                    self.btnLoginAceptar.setEnabled(False)
                    self.btnCerrarSesion.setEnabled(True)
                except Exception:
                    pass

                self.habilitar_funcionalidades()
            else:
                QMessageBox.warning(self, "Contraseña incorrecta", "La contraseña ingresada es incorrecta.")
                try:
                    self.label_estado_login.setText("Contraseña incorrecta.")
                    self.label_estado_login.setStyleSheet("color: red;")
                except Exception:
                    pass
        else:
            QMessageBox.warning(self, "Usuario no encontrado", "El usuario ingresado no existe.")
            try:
                self.label_estado_login.setText("Usuario no encontrado.")
                self.label_estado_login.setStyleSheet("color: red;")
            except Exception:
                pass


    # --------------------------------------
    # Mostrar foto Usarioo en label
    # --------------------------------------
    def mostrar_foto_usuario_en_label(self, ruta_relativa, label, size=100):
        """
        Carga la foto de usuario circular en el QLabel indicado.
        ruta_relativa: ruta relativa desde /assets/fotos_usuarios/...
        label: QLabel donde se mostrará la foto
        size: tamaño en pixeles
        """
        if ruta_relativa:
            # Limpiamos "/" o "\" inicial
            ruta_relativa = ruta_relativa.lstrip("/\\")
            ruta_completa = os.path.join(os.getcwd(), "public", ruta_relativa)

            if os.path.exists(ruta_completa):
                pixmap = QPixmap(ruta_completa).scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                pixmap_circular = QPixmap(size, size)
                pixmap_circular.fill(Qt.transparent)

                painter = QPainter(pixmap_circular)
                painter.setRenderHint(QPainter.Antialiasing)
                brush = QBrush(pixmap)
                painter.setBrush(brush)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(0, 0, size, size)
                painter.end()

                label.setPixmap(pixmap_circular)
                label.setText("")
                label.setScaledContents(True)
            else:
                label.clear()
                label.setText("Sin foto usuario")
        else:
            label.clear()
            label.setText("Sin foto usuario")


    # -------------------------
    # Sesión / permisos
    # -------------------------
    def cerrar_sesion(self):
        self.usuario_actual = None
        try:
            self.lineEdit_usuario.clear()
            self.lineEdit_password.clear()
            self.label_estado_login.setText("Sesión cerrada.")
            self.label_foto_usuario.clear()
            self.lineEdit_usuario.setEnabled(True)
            self.lineEdit_password.setEnabled(True)
            self.btnLoginAceptar.setEnabled(True)
            self.btnCerrarSesion.setEnabled(False)
        except Exception:
            pass
        self.bloquear_funcionalidades()

    def habilitar_funcionalidades(self):
        try:
            if self.rol_usuario_actual == "admin":
                self.btnGestionCargas.setVisible(True)
            else:
                self.btnRegionesZonas.setVisible(True)
                self.btnSecciones.setVisible(True)
                self.btnSubSecciones.setVisible(True)
        except Exception:
            pass

    def bloquear_funcionalidades(self):
        try:
            self.btnRegionesZonas.setVisible(False)
            self.btnSecciones.setVisible(False)
            self.btnSubSecciones.setVisible(False)
            self.btnGestionCargas.setVisible(False)
            self.btnUsuarios.setVisible(False)
            self.btnConfiguracion.setVisible(False)
        except Exception:
            pass

    def alternar_submenu_datos(self):
        mostrar = not self.btnUsuarios.isVisible()
        self.btnUsuarios.setVisible(mostrar)
        self.btnRegionesZonas.setVisible(mostrar)
        self.btnSecciones.setVisible(mostrar)
        self.btnSubSecciones.setVisible(mostrar)
        self.btnConfiguracion.setVisible(mostrar)

    def cerrar_menu_lateral(self):
        try:
            if self.frame_menu_lateral.x() == 0:
                self.animar_drawer(mostrar=False)
                if self.menu_icon_path and os.path.exists(self.menu_icon_path):
                    self.btnMenu.setIcon(QIcon(self.menu_icon_path))
                    self.btnMenu.setIconSize(QSize(40, 40))
        except Exception:
            pass

    # -------------------------
    # Abrir ventanas CRUD
    # -------------------------
    def abrir_gestion_usuarios(self):
        self.cerrar_menu_lateral()
        self.ventana_usuarios = VentanaUsuarios(parent=self)
        self.ventana_usuarios.show()
        
    def abrir_gestion_regionesZonas(self):
        self.cerrar_menu_lateral()
        self.ventana_regionesZonas = VentanaRegionesZonas(parent=self)
        self.ventana_regionesZonas.show()

    def abrir_gestion_secciones(self):
        self.cerrar_menu_lateral()
        self.ventana_secciones = VentanaSecciones(parent=self)
        self.ventana_secciones.show()

    def abrir_gestion_sub_secciones(self):
        self.cerrar_menu_lateral()
        self.ventana_sub_secciones = VentanaSubSecciones(parent=self)
        self.ventana_sub_secciones.show()

    def abrir_gestion_configuracion(self):
        self.cerrar_menu_lateral()
        self.ventana_configuracion = VentanaConfiguracion(parent=self)
        self.ventana_configuracion.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec())
