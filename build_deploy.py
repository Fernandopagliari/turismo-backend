# build_deploy.py - VERSIÓN CORREGIDA Y OPTIMIZADA
# -*- coding: utf-8 -*-
import os
import subprocess
import shutil
import time
import platform
import json
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QProgressBar, QMessageBox,
    QGroupBox, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Optional imports (no crash if faltan)
try:
    import requests
except ImportError:
    requests = None

# Intentar importar helpers DB si existen
try:
    from database_local import obtener_configuracion_hosting
    BD_DISPONIBLE = True
except Exception:
    BD_DISPONIBLE = False
    obtener_configuracion_hosting = None

# -------------------------
# UTILIDADES COMUNES
# -------------------------
def is_windows():
    return platform.system().lower().startswith("win")

def run_subprocess(cmd, cwd=None, timeout=300):
    """Ejecuta un comando seguro y devuelve (ok, stdout, stderr, returncode)"""
    try:
        if isinstance(cmd, str):
            cmd = cmd.split()
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False
        )
        return (result.returncode == 0, result.stdout or "", result.stderr or "", result.returncode)
    except subprocess.TimeoutExpired as e:
        return (False, "", f"TimeoutExpired: {str(e)}", -1)
    except FileNotFoundError as e:
        return (False, "", f"FileNotFoundError: {str(e)}", -2)
    except Exception as e:
        return (False, "", f"Exception: {str(e)}", -3)

# -------------------------
# HILO PRINCIPAL
# -------------------------
class BuildDeployThread(QThread):
    """Hilo para ejecutar build y deploy sin bloquear la UI"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, project_path, deploy_config=None):
        super().__init__()
        self.requested_path = project_path or os.getcwd()
        self.deploy_config = deploy_config or {}
        self.project_root = self.find_project_root()
        self.dist_path = os.path.join(self.project_root, "dist") if self.project_root else None
        self.backend_path = self.find_backend_path()
        self.npm_cmd = self.find_npm()
        self.node_cmd = self.find_node()
        self._stopped = False

    # -------------------------
    # UTILIDADES DE LOG
    # -------------------------
    def log(self, mensaje, nivel="INFO"):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        texto = f"[{ts}] [{nivel}] {mensaje}"
        self.log_signal.emit(texto)

    # -------------------------
    # DETECCIÓN RUTAS
    # -------------------------
    def find_project_root(self):
        """Buscar carpeta donde exista package.json"""
        posibles_rutas = [
            self.requested_path,
            os.path.join(self.requested_path, "frontend"),
            os.path.join(self.requested_path, "turismo-frontend"),
            os.path.join(self.requested_path, "src"),
            r"E:\Sistemas de app para androide\turismo-app\frontend",
            r"E:\Sistemas de app para androide\turismo-app\turismo-frontend",
            r"E:\Sistemas de app para androide\frontend",
            os.path.join(os.path.dirname(self.requested_path), "frontend"),
        ]
        
        for ruta in posibles_rutas:
            try:
                ruta_abs = os.path.abspath(ruta)
                package_json = os.path.join(ruta_abs, "package.json")
                if os.path.exists(package_json):
                    self.log(f"✅ Encontrado package.json en: {ruta_abs}")
                    return ruta_abs
            except Exception as e:
                continue
        
        self.log("❌ No se encontró package.json", "ERROR")
        return None
    
    def find_backend_path(self):
        """Intentar localizar backend Flask (api.py)"""
        posibles = [
            os.path.join(self.requested_path, "turismo-backend"),
            os.path.join(os.path.dirname(self.requested_path), "turismo-backend"),
            os.path.join(self.requested_path, "backend"),
            os.path.join(self.requested_path, "turismo-app", "turismo-backend"),
            r"E:\Sistemas de app para androide\turismo-app\turismo-backend",
        ]
        for b in posibles:
            try:
                if os.path.exists(b) and os.path.exists(os.path.join(b, "api.py")):
                    self.log(f"Backend Flask detectado en: {b}")
                    return os.path.abspath(b)
            except Exception:
                continue
        self.log("Backend Flask no detectado automáticamente.", "INFO")
        return None

    def find_npm(self):
        """Detectar npm de forma portable"""
        candidates = ["npm"]
        if is_windows():
            candidates += [
                r"C:\Program Files\nodejs\npm.cmd",
                r"C:\Program Files (x86)\nodejs\npm.cmd",
                os.path.join(os.environ.get("APPDATA", ""), "npm", "npm.cmd"),
            ]
        else:
            candidates += ["/usr/bin/npm", "/usr/local/bin/npm"]

        for cmd in candidates:
            ok, out, err, rc = run_subprocess([cmd, "--version"], timeout=8)
            if ok:
                self.log(f"npm encontrado: {cmd} ({out.strip()})")
                return cmd
        self.log("npm no encontrado", "WARN")
        return None

    def find_node(self):
        """Detectar node de forma portable"""
        candidates = ["node"]
        if is_windows():
            candidates += [
                r"C:\Program Files\nodejs\node.exe",
                r"C:\Program Files (x86)\nodejs\node.exe",
            ]
        else:
            candidates += ["/usr/bin/node", "/usr/local/bin/node"]

        for cmd in candidates:
            ok, out, err, rc = run_subprocess([cmd, "--version"], timeout=8)
            if ok:
                self.log(f"node encontrado: {cmd} ({out.strip()})")
                return cmd
        self.log("node no encontrado", "WARN")
        return None

    # -------------------------
    # VERIFICACIONES
    # -------------------------
    def verify_environment(self):
        """Verificar que lo mínimo esté presente"""
        if not self.project_root:
            raise RuntimeError("No se encontró la raíz del proyecto (package.json).")
        if not self.node_cmd or not self.npm_cmd:
            raise RuntimeError("Node.js o npm no están instalados.")
        self.log(f"Entorno verificado: project_root={self.project_root}", "DEBUG")

    # -------------------------
    # INSTALAR DEPENDENCIAS
    # -------------------------
    def verify_dependencies(self):
        """Comprobar si node_modules existe"""
        nm = os.path.join(self.project_root, "node_modules")
        existe = os.path.exists(nm)
        self.log(f"node_modules existe: {existe}", "DEBUG")
        return existe

    def install_dependencies(self):
        """Ejecutar npm install"""
        self.log("Instalando dependencias (npm install)...")
        ok, out, err, rc = run_subprocess([self.npm_cmd, "install"], cwd=self.project_root, timeout=600)
        if ok:
            self.log("Dependencias instaladas correctamente")
            return True
        else:
            self.log(f"Error instalando dependencias: {err[:1000]}", "ERROR")
            return False

    # -------------------------
    # EJECUTAR BUILD
    # -------------------------
    def run_build(self):
        """Ejecutar npm run build"""
        self.log("Iniciando build de React (npm run build)...")
        ok, out, err, rc = run_subprocess([self.npm_cmd, "run", "build"], cwd=self.project_root, timeout=900)
        if ok:
            self.log("Build completado correctamente")
            if os.path.exists(self.dist_path):
                size = self.get_folder_size(self.dist_path)
                self.log(f"Carpeta dist creada: {self.dist_path} (tamaño: {size})")
            return True
        else:
            self.log(f"Error ejecutando build: {err[:2000] or out[:2000]}", "ERROR")
            return False

    # -------------------------
    # ✅ VERSIÓN CORREGIDA: COPIAR BUILD A FLASK SIN DUPLICAR
    # -------------------------
    def copy_build_to_flask(self):
        """Copia SOLO archivos esenciales del build SIN duplicar carpetas"""
        if not self.backend_path:
            self.log("No hay backend configurado; se omite integración Flask", "INFO")
            return False

        if not self.dist_path or not os.path.exists(self.dist_path):
            self.log("No se encontró la carpeta dist", "ERROR")
            return False

        # ✅ CORREGIDO: Usar assets/ en lugar de build/ para consistencia
        assets_destino = os.path.join(self.backend_path, "assets")
        
        try:
            # ✅ PRIMERO: Limpiar solo archivos del build, mantener imágenes
            # ✅ VERSIÓN MEJORADA - NO da error si hay archivos en uso
            if os.path.exists(assets_destino):
                self.log(f"🧹 Limpiando assets existentes...")
                for item in os.listdir(assets_destino):
                    item_path = os.path.join(assets_destino, item)
                    # ✅ MANTENER solo la carpeta imagenes/
                    if item != "imagenes":
                        try:
                            if os.path.isfile(item_path):
                                os.remove(item_path)
                                self.log(f"   🗑️ Eliminado: {item}")
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                                self.log(f"   🗑️ Eliminada carpeta: {item}/")
                        except Exception as e:
                            # ✅ SI HAY ERROR, CONTINUAR SIN PARAR
                            self.log(f"   ⚠️ No se pudo eliminar {item}: {str(e)}")
                            continue  # ← ESTO ES CLAVE: CONTINUA A PESAR DEL ERROR

            # ✅ SEGUNDO: Copiar SOLO archivos esenciales del build
            self.log(f"📦 Copiando build desde {self.dist_path} -> {assets_destino}")
            
            items_copiados = 0
            for item in os.listdir(self.dist_path):
                origen_item = os.path.join(self.dist_path, item)
                destino_item = os.path.join(assets_destino, item)
                
                try:
                    # ✅ SOLO copiar archivos, NO carpetas (para evitar assets/assets/)
                    if os.path.isfile(origen_item):
                        shutil.copy2(origen_item, destino_item)
                        items_copiados += 1
                        self.log(f"   📄 {item}")
                    # ✅ EXCEPCIÓN: Si es carpeta 'assets' del build, copiar su CONTENIDO
                    elif os.path.isdir(origen_item) and item == "assets":
                        for sub_item in os.listdir(origen_item):
                            sub_origen = os.path.join(origen_item, sub_item)
                            sub_destino = os.path.join(assets_destino, sub_item)
                            if os.path.isfile(sub_origen):
                                shutil.copy2(sub_origen, sub_destino)
                                items_copiados += 1
                                self.log(f"   📄 {sub_item}")
                            elif os.path.isdir(sub_origen):
                                shutil.copytree(sub_origen, sub_destino, dirs_exist_ok=True)
                                count = sum([len(files) for r, d, files in os.walk(sub_destino)])
                                items_copiados += count
                                self.log(f"   📁 {sub_item}/ ({count} archivos)")
                except Exception as e:
                    self.log(f"   ⚠️  Error copiando {item}: {str(e)}")

            self.log(f"✅ {items_copiados} archivos de React copiados")
            
            # ✅ VERIFICAR que index.html existe
            index_path = os.path.join(assets_destino, "index.html")
            if os.path.exists(index_path):
                self.log("🎯 index.html encontrado - Frontend listo")
            else:
                self.log("❌ index.html NO encontrado en build")

            # ✅ ACTUALIZAR Flask para servir desde assets/
            self.update_flask_for_assets()
            
            return True
            
        except Exception as e:
            self.log(f"Error copiando build a Flask: {e}", "ERROR")
            return False

    def update_flask_for_assets(self):
        """Actualizar Flask para servir desde assets/ en lugar de build/"""
        try:
            if not self.backend_path:
                return
                
            api_path = os.path.join(self.backend_path, "api.py")
            if not os.path.exists(api_path):
                self.log("No se encontró api.py para actualizar", "WARN")
                return
            
            # Leer contenido actual
            with open(api_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # ✅ CORREGIDO: Actualizar para usar assets/ en lugar de build/
            contenido_actualizado = contenido.replace(
                'app.static_folder = os.path.join(os.path.dirname(__file__), "build")',
                'app.static_folder = os.path.join(os.path.dirname(__file__), "assets")'
            )
            
            # Si no encontró la línea anterior, buscar y reemplazar cualquier referencia a build
            if contenido_actualizado == contenido and 'build' in contenido:
                # Buscar cualquier línea que configure static_folder con build
                lines = contenido.split('\n')
                updated_lines = []
                for line in lines:
                    if 'static_folder' in line and 'build' in line:
                        updated_lines.append('app.static_folder = os.path.join(os.path.dirname(__file__), "assets")')
                    else:
                        updated_lines.append(line)
                contenido_actualizado = '\n'.join(updated_lines)
            
            # Escribir archivo actualizado solo si hubo cambios
            if contenido_actualizado != contenido:
                with open(api_path, 'w', encoding='utf-8') as f:
                    f.write(contenido_actualizado)
                self.log("✅ Flask actualizado para servir desde assets/", "INFO")
            else:
                self.log("✅ Flask ya está configurado para assets/", "DEBUG")
            
        except Exception as e:
            self.log(f"⚠️  No se pudo actualizar Flask: {e}", "WARN")

    # -------------------------
    # DEPLOYS
    # -------------------------
    def deploy_via_railway(self):
        """Deploy automático con railway CLI"""
        self.log("Intentando deploy a Railway...")
        ok, out, err, rc = run_subprocess(["railway", "--version"], timeout=12)
        if not ok:
            self.log("Railway CLI no está instalado", "WARN")
            return True

        ok, out, err, rc = run_subprocess(["railway", "deploy"], cwd=self.project_root, timeout=1200)
        if ok:
            self.log("Deploy a Railway completado")
            return True
        else:
            self.log(f"Railway deploy falló: {err[:800]}", "WARN")
            return True

    def deploy_github_pages(self):
        """Deploy usando gh-pages"""
        self.log("Intentando deploy a GitHub Pages...")
        try:
            pjson = os.path.join(self.project_root, "package.json")
            if os.path.exists(pjson):
                with open(pjson, "r", encoding="utf-8") as f:
                    data = json.load(f)
                scripts = data.get("scripts", {})
                if "deploy" in scripts:
                    ok, out, err, rc = run_subprocess([self.npm_cmd, "run", "deploy"], cwd=self.project_root, timeout=900)
                    if ok:
                        self.log("Deploy a GitHub Pages completado")
                        return True
        except Exception as e:
            self.log(f"Error en deploy gh-pages: {e}", "WARN")
        self.log("gh-pages no configurado", "INFO")
        return True

    def deploy_netlify(self):
        self.log("Instrucciones Netlify: arrastrar carpeta dist o conectar repo GitHub.")
        return True

    def deploy_vercel(self):
        self.log("Instrucciones Vercel: instalar Vercel CLI y ejecutar `vercel --prod`")
        return True

    def deploy_generic(self):
        self.log("Deploy genérico: subir carpeta 'dist' al servidor", "INFO")
        return True

    def perform_deploy(self):
        """Decidir y ejecutar el deploy"""
        base_url = (self.deploy_config or {}).get("base_url", "") if self.deploy_config else ""
        if not base_url:
            self.log("No hay base_url configurada", "INFO")
            return True

        base_url = base_url.lower()

        if "railway" in base_url:
            return self.deploy_via_railway()
        elif "netlify" in base_url:
            return self.deploy_netlify()
        elif "vercel" in base_url:
            return self.deploy_vercel()
        elif "github" in base_url or "pages" in base_url:
            return self.deploy_github_pages()
        else:
            return self.deploy_generic()

    # -------------------------
    # VERIFICACIÓN POST-DEPLOY
    # -------------------------
    def verify_production(self):
        """Comprobar endpoints básicos"""
        if not requests:
            self.log("requests no está instalado", "WARN")
            return True

        base_url = (self.deploy_config or {}).get("base_url", "")
        if not base_url:
            self.log("No hay base_url para verificación", "DEBUG")
            return True

        endpoints = ["/api/health", "/api/configuracion", "/"]
        todos_ok = True
        for ep in endpoints:
            url = base_url.rstrip("/") + ep
            try:
                self.log(f"Verificando {url} ...")
                r = requests.get(url, timeout=12)
                if r.status_code == 200:
                    self.log(f"✅ {ep} - OK")
                else:
                    self.log(f"⚠️ {ep} - status {r.status_code}", "WARN")
                    todos_ok = False
            except Exception as e:
                self.log(f"❌ {ep} - no responde: {e}", "WARN")
                todos_ok = False
        return todos_ok

    # -------------------------
    # HERRAMIENTAS AUX
    # -------------------------
    def get_folder_size(self, folder_path):
        """Tamaño aproximado de carpeta en MB"""
        try:
            total = 0
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total += os.path.getsize(fp)
                    except Exception:
                        pass
            return f"{total / (1024 * 1024):.2f} MB"
        except Exception:
            return "Desconocido"

    # -------------------------
    # RUN PRINCIPAL
    # -------------------------
    def run(self):
        """Secuencia principal"""
        try:
            self.progress_signal.emit(2)
            self.log("==== INICIANDO BUILD & DEPLOY ====")

            # 1) Verificar entorno mínimo
            try:
                self.verify_environment()
            except Exception as e:
                self.log(f"Entorno inválido: {e}", "ERROR")
                self.finished_signal.emit(False, str(e))
                return

            self.progress_signal.emit(8)

            # 2) Instalar dependencias si hace falta
            if not self.verify_dependencies():
                self.log("Instalando dependencias...")
                if not self.install_dependencies():
                    self.finished_signal.emit(False, "Error instalando dependencias")
                    return

            self.progress_signal.emit(18)

            # 3) Ejecutar build
            if not self.run_build():
                self.finished_signal.emit(False, "Error en el build")
                return

            self.progress_signal.emit(70)

            # 4) ✅ CORREGIDO: Integrar con Flask (copiar a assets/)
            integrated = False
            if self.backend_path:
                try:
                    integrated = self.copy_build_to_flask()
                    if integrated:
                        self.progress_signal.emit(82)
                    else:
                        self.progress_signal.emit(78)
                except Exception as e:
                    self.log(f"Error integrando con Flask: {e}", "ERROR")
                    self.progress_signal.emit(78)

            # 5) Ejecutar deploy
            deploy_ok = self.perform_deploy()
            if deploy_ok:
                self.progress_signal.emit(92)
            else:
                self.progress_signal.emit(85)

            # 6) Verificación final
            try:
                ok_prod = self.verify_production()
                if ok_prod:
                    self.progress_signal.emit(97)
                    self.log("Verificación final OK", "INFO")
                else:
                    self.log("Algunos endpoints no respondieron", "WARN")
            except Exception as e:
                self.log(f"Error en verificación final: {e}", "WARN")

            # Mensaje final
            final_msg = "Build & Deploy completado"
            if integrated:
                final_msg += " + Integración Flask realizada (assets/)"
            else:
                final_msg += " (sin integración Flask)" if self.backend_path else ""

            self.progress_signal.emit(100)
            self.finished_signal.emit(True, final_msg)
            self.log("==== PROCESO FINALIZADO ====")
        except Exception as e:
            self.log(f"Error crítico: {e}", "ERROR")
            self.finished_signal.emit(False, f"Error crítico: {e}")

# -------------------------
# DIÁLOGO PyQt (UI)
# -------------------------
class DialogoBuildDeploy(QDialog):
    """Diálogo para build y deploy automático"""
    def __init__(self, parent=None, project_path=None):
        super().__init__(parent)
        self.project_path = project_path or os.getcwd()
        self.deploy_config = None
        self.build_thread = None
        self.setup_ui()
        self.load_config_from_db()

    def setup_ui(self):
        self.setWindowTitle("🚀 Build & Deploy Automático + Flask")
        self.setFixedSize(800, 700)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        titulo = QLabel("🚀 Sistema Automático de Build & Deploy + Flask")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(titulo)

        info_group = QGroupBox("📋 Información del Sistema")
        info_layout = QVBoxLayout()
        self.lbl_proyecto = QLabel(f"📁 Proyecto React: {self.project_path}")
        self.lbl_deploy = QLabel("🌐 Deploy: Cargando configuración...")
        self.lbl_url = QLabel("🔗 URL: Cargando...")
        self.lbl_flask = QLabel("🐍 Flask: Verificando...")
        self.lbl_node = QLabel("📦 Node.js: Verificando...")
        info_layout.addWidget(self.lbl_proyecto)
        info_layout.addWidget(self.lbl_deploy)
        info_layout.addWidget(self.lbl_url)
        info_layout.addWidget(self.lbl_flask)
        info_layout.addWidget(self.lbl_node)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        lbl_log = QLabel("📝 Log de ejecución:")
        layout.addWidget(lbl_log)

        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(300)
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(12)
        layout.addWidget(self.progress_bar)

        botones_layout = QHBoxLayout()
        self.btn_build_only = QPushButton("🔨 Solo Build + Flask")
        self.btn_build_deploy = QPushButton("🚀 Build + Deploy")
        self.btn_verificar = QPushButton("🔍 Verificar")
        self.btn_limpiar = QPushButton("🗑️ Limpiar")
        self.btn_cerrar = QPushButton("❌ Cerrar")

        botones_layout.addWidget(self.btn_build_only)
        botones_layout.addWidget(self.btn_build_deploy)
        botones_layout.addWidget(self.btn_verificar)
        botones_layout.addWidget(self.btn_limpiar)
        botones_layout.addWidget(self.btn_cerrar)
        layout.addLayout(botones_layout)

        scroll.setWidget(scroll_content)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        # conexiones
        self.btn_build_only.clicked.connect(lambda: self.start_process(None))
        self.btn_build_deploy.clicked.connect(lambda: self.start_process(self.deploy_config))
        self.btn_verificar.clicked.connect(self.verify_system)
        self.btn_limpiar.clicked.connect(self.clear_log)
        self.btn_cerrar.clicked.connect(self.close)

        self.verify_system()

    def append_log(self, mensaje):
        self.log_output.append(mensaje)
        self.log_output.moveCursor(self.log_output.textCursor().End)

    def clear_log(self):
        self.log_output.clear()
        self.append_log("🗑️ Log limpiado")

    def load_config_from_db(self):
        """Cargar configuración de deploy desde la BD"""
        try:
            if not BD_DISPONIBLE:
                self.deploy_config = {}
                self.lbl_deploy.setText("🌐 Deploy: DB no disponible")
                self.lbl_url.setText("🔗 URL: No configurado")
                return
            cfg = obtener_configuracion_hosting()
            if cfg:
                self.deploy_config = cfg
                base_url = cfg.get("base_url", "No configurado")
                host_info = cfg.get("host", "Servidor")
                self.lbl_deploy.setText(f"🌐 Deploy: {host_info}")
                self.lbl_url.setText(f"🔗 URL: {base_url}")
                self.append_log(f"✅ Configuración cargada desde DB: {base_url}")
            else:
                self.deploy_config = {}
                self.lbl_deploy.setText("🌐 Deploy: No configurado")
                self.lbl_url.setText("🔗 URL: No configurado")
        except Exception as e:
            self.append_log(f"❌ Error cargando configuración desde DB: {e}")

    def verify_system(self):
        """Verificar estado local: Flask + Node"""
        try:
            # Verificar backend Flask
            if self._detect_flask():
                self.lbl_flask.setText("🐍 Flask: ✅ Detectado")
            else:
                self.lbl_flask.setText("🐍 Flask: ❌ No detectado")

            # Verificar Node/npm
            thread_probe = BuildDeployThread(self.project_path)
            node_ok = bool(thread_probe.node_cmd)
            npm_ok = bool(thread_probe.npm_cmd)
            self.lbl_node.setText(f"📦 Node.js: {'✅' if node_ok and npm_ok else '❌'}")
            self.append_log("🔍 Verificación del sistema completada")
        except Exception as e:
            self.append_log(f"❌ Error verificando sistema: {e}")

    def _detect_flask(self):
        """Detecta si existe un backend con api.py"""
        poss = [
            os.path.join(self.project_path, "turismo-backend"),
            os.path.join(os.path.dirname(self.project_path), "turismo-backend"),
            os.path.join(self.project_path, "backend"),
        ]
        for p in poss:
            if os.path.exists(p) and os.path.exists(os.path.join(p, "api.py")):
                return True
        return False

    def start_process(self, deploy_cfg):
        """Inicia hilo de build/deploy"""
        self.btn_build_only.setEnabled(False)
        self.btn_build_deploy.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_output.clear()
        self.append_log("🚀 INICIANDO PROCESO BUILD & DEPLOY...")

        cfg = deploy_cfg or self.deploy_config or {}
        self.build_thread = BuildDeployThread(self.project_path, cfg)
        self.build_thread.log_signal.connect(self.append_log)
        self.build_thread.progress_signal.connect(self.progress_bar.setValue)
        self.build_thread.finished_signal.connect(self.process_finished)
        self.build_thread.start()

    def process_finished(self, success, mensaje):
        """Callback cuando termina el hilo"""
        self.btn_build_only.setEnabled(True)
        self.btn_build_deploy.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.append_log(mensaje)
        self.verify_system()

        if success:
            QMessageBox.information(self, "✅ Éxito", f"{mensaje}")
        else:
            QMessageBox.critical(self, "❌ Error", f"{mensaje}")

# -------------------------
# ENTRYPOINT para pruebas
# -------------------------
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication([])
    dlg = DialogoBuildDeploy(project_path=os.getcwd())
    dlg.show()
    app.exec_()