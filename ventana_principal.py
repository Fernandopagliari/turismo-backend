# -*- coding: utf-8 -*-
# ventana_principal.py - VERSIÓN CON BÚSQUEDA REMOTO → LOCAL Y CACHE
import os
import sys
import requests
import time
import hashlib
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox
from PyQt5 import uic
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QSize

# ✅ CAMBIADO: Importar la función correcta
#from database_local import conectar_local as conectar_base_datos
from database_hosting import conectar_hosting as conectar_base_datos # ← Para cuando necesites conectar al hosting

from app_usuarios import VentanaUsuarios
from app_secciones import VentanaSecciones
from app_sub_secciones import VentanaSubSecciones
from app_configuracion import VentanaConfiguracion
from app_regiones_zonas import VentanaRegionesZonas
from build_deploy import DialogoBuildDeploy
from backend_deploy import DialogoBackendDeploy

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

def cargar_imagen_desde_ruta_con_cache(ruta_imagen: str, size: tuple = None):
    """
    Carga imagen desde URL remota o archivo local - CON CACHE
    (Función auxiliar para usar el sistema de cache)
    """
    if not ruta_imagen:
        return None

    # Limpiar cache antiguo periódicamente
    if len(_image_cache) > _CACHE_MAX_SIZE:
        limpiar_cache_antiguo()

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
            response = requests.get(ruta_imagen, timeout=10)  # Timeout aumentado para redes lentas
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
        print(f"Error cargando imagen {ruta_imagen}: {e}")
        return None

def _is_url(path):
    """Verifica si una ruta es una URL"""
    return isinstance(path, str) and (path.startswith("http://") or path.startswith("https://"))

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
        self.base_url = None  # ✅ NUEVO: Para almacenar URL base del hosting

        # Mover el menú lateral fuera de pantalla inicialmente
        try:
            self.frame_menu_lateral.move(-self.frame_menu_lateral.width(), self.btnMenu.height())
        except Exception:
            pass

        # Maximizar ventana
        self.showMaximized()

        # ✅ PRIMERO: Obtener URL base del hosting para imágenes remotas
        self.obtener_url_base_hosting()

        # Cargar configuración (iconos, hero) desde la BD
        self.cargar_configuracion()

        # Configurar interfaz (con iconos según BD o fallback)
        self.configurar_interfaz()

        # Cargar imagen central (hero)
        self.cargar_imagen_central()
        
    # -------------------------
    # NUEVO MÉTODO: Obtener URL base del hosting
    # -------------------------
    def obtener_url_base_hosting(self):
        """
        Obtiene la URL base del hosting desde la BD
        Esto es esencial para construir URLs remotas correctas
        """
        try:
            conn = conectar_base_datos()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT base_url FROM datos_hosting WHERE activo = 1 LIMIT 1")
            resultado = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if resultado and resultado.get('base_url'):
                self.base_url = resultado['base_url'].strip()
                # Asegurar que base_url termine con /
                if self.base_url and not self.base_url.endswith('/'):
                    self.base_url += '/'
                print(f"[HOSTING] URL base configurada: {self.base_url}")
            else:
                print("[HOSTING] No se encontró URL base en la BD")
                self.base_url = None
                
        except Exception as e:
            print(f"[HOSTING] Error obteniendo URL base: {e}")
            self.base_url = None

    def obtener_url_remota(self, ruta_relativa: str) -> str:
        """
        Construye URL remota basada en la configuración de hosting
        """
        if not self.base_url or not ruta_relativa:
            return ""

        try:
            # Limpiar y normalizar la ruta relativa
            ruta_limpia = ruta_relativa.replace("\\", "/").lstrip('/')
            
            # Si la ruta ya contiene 'assets/', usarla directamente
            if "assets/" in ruta_limpia:
                # Extraer la parte después de 'assets/'
                partes = ruta_limpia.split("assets/", 1)
                if len(partes) > 1:
                    ruta_limpia = f"assets/{partes[1]}"
            
            # Construir URL completa
            url_completa = f"{self.base_url}{ruta_limpia}"
            return url_completa
            
        except Exception as e:
            print(f"Error construyendo URL remota: {e}")
            return ""

    def verificar_url_remota(self, url: str) -> bool:
        """
        Verifica si una URL remota es accesible - OPTIMIZADA
        """
        if not url:
            return False
            
        try:
            response = requests.head(url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"URL no accesible {url}: {e}")
            return False

    def mostrar_imagen_desde_url(self, url: str):
        """
        Carga y muestra imagen desde URL remota - CON CACHE
        """
        try:
            # ✅ OPTIMIZADO: Usar sistema de cache
            pixmap = cargar_imagen_desde_ruta_con_cache(url, 
                (self.label_imagen_central.width(), self.label_imagen_central.height()))
            
            if pixmap and not pixmap.isNull():
                self.label_imagen_central.setPixmap(pixmap)
                self.label_imagen_central.setAlignment(Qt.AlignCenter)
                print(f"✅ Imagen remota cargada: {url}")
            else:
                print("❌ No se pudo cargar imagen desde URL")
                self.mostrar_imagen_alternativa()
                
        except Exception as e:
            print(f"❌ Error cargando imagen desde URL: {e}")
            self.mostrar_imagen_alternativa()
        
    # -------------------------
    # Helpers: resolver rutas - MODIFICADO PARA PRIORIZAR REMOTO
    # -------------------------
    def _is_url(self, path):
        """Verifica si una ruta es una URL - MÉTODO DE INSTANCIA"""
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
        MODIFICADO: Primero busca en REMOTO, luego en LOCAL
        (incluye project_root/public como ubicación válida)
        """
        if not ruta:
            return None

        ruta_raw = ruta
        ruta = ruta.replace("\\", "/").strip()

        # ✅ 1. PRIMERO: Ver si es URL directa
        if self._is_url(ruta):
            #print(f"[resolve_asset_path] Ruta es URL directa: {ruta}")
            if self.verificar_url_remota(ruta):
                return ruta
            else:
                print(f"[resolve_asset_path] URL directa no accesible: {ruta}")

        # ✅ 2. INTENTAR REPOSITORIO REMOTO
        #print(f"[resolve_asset_path] Intentando repositorio REMOTO para: {ruta}")
        url_remota = self.obtener_url_remota(ruta)
        if url_remota and self.verificar_url_remota(url_remota):
            #print(f"[resolve_asset_path] ✅ Encontrado en REMOTO: {url_remota}")
            return url_remota

        # ✅ 3. SEGUNDO: Buscar en LOCAL
        #print(f"[resolve_asset_path] No encontrado en REMOTO, buscando en LOCAL...")

        # Ruta absoluta directa
        if os.path.isabs(ruta) and os.path.exists(ruta):
            p = os.path.normpath(ruta)
            print(f"[resolve_asset_path] Ruta absoluta encontrada: {p}")
            return p

        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(backend_dir, "..", ".."))

        cleaned = self._normalize_db_path(ruta)

        candidates = []

        # 🔥 0) project_root/public/<cleaned>  (ESTA ES LA CLAVE)
        candidates.append(os.path.join(project_root, "public", cleaned))

        # 1) frontend/public/<cleaned>
        candidates.append(os.path.join(project_root, "frontend", "public", cleaned))

        # 2) frontend/src y assets
        candidates.append(os.path.join(project_root, "frontend", "src", cleaned))
        candidates.append(os.path.join(project_root, "frontend", "src", "assets", cleaned))

        # 3) frontend/assets
        candidates.append(os.path.join(project_root, "frontend", "assets", cleaned))

        # 4) builds
        candidates.append(os.path.join(project_root, "frontend", "dist", "assets", cleaned))
        candidates.append(os.path.join(project_root, "frontend", "build", "assets", cleaned))

        # 5) project_root directo
        candidates.append(os.path.join(project_root, cleaned))

        # 6) assets y static en raíz
        candidates.append(os.path.join(project_root, "assets", cleaned))
        candidates.append(os.path.join(project_root, "static", cleaned))

        # 7) backend
        candidates.append(os.path.join(backend_dir, cleaned))

        # 8) rutas crudas por si BD guardó algo raro
        candidates.append(os.path.normpath(os.path.join(project_root, ruta_raw)))
        candidates.append(os.path.normpath(os.path.join(backend_dir, ruta_raw)))

        # 9) cwd
        candidates.append(os.path.normpath(os.path.join(os.getcwd(), cleaned)))

        # Debug
        #print("[resolve_asset_path] Candidatas LOCALES (en este orden):")
        for c in candidates:
            try:
                print("   -", c, " -> exists:", os.path.exists(c))
            except Exception:
                print("   -", c, " -> exists: (error comprobando)")

        # Resolver
        for p in candidates:
            try:
                if p and os.path.exists(p):
                    pnorm = os.path.normpath(p)
                    #print(f"[resolve_asset_path] ✅ Encontrado en LOCAL: {pnorm}")
                    return pnorm
            except Exception:
                pass

        # Búsqueda de ayuda
        basename = os.path.basename(cleaned)
        #print(f"[resolve_asset_path] No se encontró archivo en candidatas. Buscando '{basename}' dentro de {project_root}...")
        matches = self._search_for_filename_in_project(basename, project_root, max_matches=20)
        if matches:
            #print("[resolve_asset_path] Se encontraron coincidencias en el repo:")
            for m in matches:
                print("   -", m)
        else:
            print("[resolve_asset_path] No se encontró ninguna coincidencia del nombre de archivo.")

        #print("[resolve_asset_path] ❌ No se encontró archivo en REMOTO ni LOCAL.")
        return None


    def find_asset_or_fallback(self, ruta_bd, fallback_relative):
        """
        MODIFICADO: Ahora maneja URLs remotas también
        """
        # 1) intentar BD
        if ruta_bd:
            ruta_res = self.resolve_asset_path(ruta_bd)
            
            if ruta_res:
                # si es URL, devolvemos la URL (ahora sí la podemos cargar)
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
    # Interfaz / iconos navbar - MODIFICADO PARA GARANTIZAR QUE SE MUESTREN
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

        # ✅ MODIFICADO: Cargar iconos usando el mismo método que la imagen de usuario
        self.cargar_icono_menu()
        
        try:
            self.btnBackendDeploy.setVisible(False)
            self.btnBuildDeploy.setVisible(False)
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
            self.btnBuildDeploy.clicked.connect(self.abrir_gestion_buildDeploy)
            self.btnBackendDeploy.clicked.connect(self.abrir_gestion_backendDeploy)
        except Exception as e:
            print("Error conectando botones:", e)
            pass

        self.usuario_actual = None
        try:
            self.label_estado_login.setText("No hay sesión iniciada.")
        except Exception:
            pass
        self.bloquear_funcionalidades()

    # -------------------------
    # NUEVO MÉTODO: Cargar icono del menú de forma robusta
    # -------------------------
    def cargar_icono_menu(self):
        """Carga el icono del menú de forma robusta, similar a como se carga la imagen de usuario"""
        try:
            if self.menu_icon_path:
                # ✅ OPTIMIZADO: Usar sistema de cache
                pixmap = cargar_imagen_desde_ruta_con_cache(self.menu_icon_path, (40, 40))
                if pixmap and not pixmap.isNull():
                    self.btnMenu.setIcon(QIcon(pixmap))
                    self.btnMenu.setIconSize(QSize(40, 40))
                    return
                
            # Si llegamos aquí, usar icono por defecto
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(backend_dir, "..", ".."))
            default_icon = os.path.join(project_root, "frontend", "public", "assets", "iconos", "menu.png")
            
            if os.path.exists(default_icon):
                pixmap = QPixmap(default_icon)
                if not pixmap.isNull():
                    self.btnMenu.setIcon(QIcon(pixmap))
                    self.btnMenu.setIconSize(QSize(40, 40))
        except Exception as e:
            print("Error cargando icono menú:", e)
            pass

    # -------------------------
    # Imagen central (hero) - MODIFICADO CON CACHE Y MÁS ROBUSTO
    # -------------------------
    def cargar_imagen_central(self):
        """
        Carga la imagen hero - AHORA maneja URLs remotas CON CACHE
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

            # ✅ MODIFICADO: Usar el mismo método robusto que para los iconos
            ruta_resuelta = self.find_asset_or_fallback(ruta_relativa, "assets/imagenes/hongo_ischigualasto.jpg")
            print(f"[HERO] Intentando cargar imagen central desde: {ruta_resuelta}")

            if ruta_resuelta:
                # ✅ MANEJAR URL REMOTA CON CACHE
                if self._is_url(ruta_resuelta):
                    print(f"[HERO] Cargando desde URL remota: {ruta_resuelta}")
                    self.mostrar_imagen_desde_url(ruta_resuelta)
                    return

                # ✅ MANEJAR ARCHIVO LOCAL CON CACHE
                if os.path.exists(ruta_resuelta):
                    # ✅ OPTIMIZADO: Usar sistema de cache
                    pixmap = cargar_imagen_desde_ruta_con_cache(ruta_resuelta, 
                        (self.label_imagen_central.width(), self.label_imagen_central.height()))
                    
                    if pixmap and not pixmap.isNull():
                        self.label_imagen_central.setPixmap(pixmap)
                        self.label_imagen_central.setAlignment(Qt.AlignCenter)
                        self.label_imagen_central.setStyleSheet("")
                        print(f"✅ Imagen central cargada: {ruta_resuelta}")
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
        """Muestra una imagen alternativa o texto si no se puede cargar la imagen principal"""
        try:
            # Intentar cargar imagen de respaldo
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(backend_dir, "..", ".."))
            fallback_image = os.path.join(project_root, "frontend", "public", "assets", "imagenes", "hongo_ischigualasto.jpg")
            
            if os.path.exists(fallback_image):
                pixmap = QPixmap(fallback_image)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        self.label_imagen_central.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.label_imagen_central.setPixmap(scaled)
                    self.label_imagen_central.setAlignment(Qt.AlignCenter)
                    return
            
            # Si no hay imagen de respaldo, mostrar texto
            self.label_imagen_central.setText("Imagen no disponible")
            self.label_imagen_central.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    color: #666;
                    qproperty-alignment: AlignCenter;
                }
            """)
        except Exception:
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
    # Drawer (menu lateral) - OPTIMIZADO CON CACHE
    # -------------------------
    def mostrar_menu_lateral(self):
        self.animar_drawer(mostrar=True)
        # ✅ OPTIMIZADO: Cargar icono de cerrar usando cache
        self.cargar_icono_cerrar()

    def alternar_menu_lateral(self):
        esta_oculto = self.frame_menu_lateral.x() < 0
        self.animar_drawer(esta_oculto)
        
        # ✅ OPTIMIZADO: Cargar iconos usando cache
        if esta_oculto:
            self.cargar_icono_cerrar()
        else:
            self.cargar_icono_menu()

    def cargar_icono_cerrar(self):
        """Carga el icono de cerrar de forma robusta"""
        try:
            if self.close_icon_path:
                # ✅ OPTIMIZADO: Usar sistema de cache
                pixmap = cargar_imagen_desde_ruta_con_cache(self.close_icon_path, (40, 40))
                if pixmap and not pixmap.isNull():
                    self.btnMenu.setIcon(QIcon(pixmap))
                    self.btnMenu.setIconSize(QSize(40, 40))
                    return
                
            # Si llegamos aquí, usar icono por defecto
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(backend_dir, "..", ".."))
            default_icon = os.path.join(project_root, "frontend", "public", "assets", "iconos", "cerrar.png")
            
            if os.path.exists(default_icon):
                pixmap = QPixmap(default_icon)
                if not pixmap.isNull():
                    self.btnMenu.setIcon(QIcon(pixmap))
                    self.btnMenu.setIconSize(QSize(40, 40))
        except Exception as e:
            print("Error cargando icono cerrar:", e)
            pass

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

                # Mostrar foto de usuario (resolver ruta) - CON CACHE
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
    # Mostrar foto Usario en label - MODIFICADO CON CACHE
    # --------------------------------------
    def mostrar_foto_usuario_en_label(self, ruta_relativa, label, size=100):
        print("📸 FOTO USUARIO (BD):", ruta_relativa)
        """
        Carga la foto de usuario circular en el QLabel indicado.
        AHORA maneja URLs remotas también CON CACHE.
        """
        if ruta_relativa:
            # Resolver ruta (puede ser local o remota)
            ruta_resuelta = self.find_asset_or_fallback(ruta_relativa, "assets/iconos/usuario_default.png")
            
            if ruta_resuelta:
                # ✅ OPTIMIZADO: Usar sistema de cache
                pixmap = cargar_imagen_desde_ruta_con_cache(ruta_resuelta, (size, size))
                
                if pixmap and not pixmap.isNull():
                    # Crear imagen circular
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
                    label.setText("Sin foto")
            else:
                label.clear()
                label.setText("Sin foto")
        else:
            label.clear()
            label.setText("Sin foto")

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
            self.btnBuildDeploy.setVisible(False)
            self.btnBackendDeploy.setVisible(False)
        except Exception:
            pass

    def alternar_submenu_datos(self):
        mostrar = not self.btnUsuarios.isVisible()
        self.btnUsuarios.setVisible(mostrar)
        self.btnRegionesZonas.setVisible(mostrar)
        self.btnSecciones.setVisible(mostrar)
        self.btnSubSecciones.setVisible(mostrar)
        self.btnConfiguracion.setVisible(mostrar)
        self.btnBuildDeploy.setVisible(mostrar)
        self.btnBackendDeploy.setVisible(mostrar)

    def cerrar_menu_lateral(self):
        try:
            if self.frame_menu_lateral.x() == 0:
                self.animar_drawer(mostrar=False)
                self.cargar_icono_menu()
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

    def abrir_gestion_buildDeploy(self):
        self.cerrar_menu_lateral()
        self.ventana_buildDeploy = DialogoBuildDeploy(parent=self)
        self.ventana_buildDeploy.show()
        
    def abrir_gestion_backendDeploy(self):
        self.cerrar_menu_lateral()
        self.ventana_backendDeploy = DialogoBackendDeploy(parent=self)
        self.ventana_backendDeploy.show()
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec())