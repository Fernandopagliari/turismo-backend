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
    obtener_configuracion_hosting = None  # ✅ AGREGADO para evitar errores


# -------------------------
# UTILIDADES COMUNES
# -------------------------
def is_windows():
    return platform.system().lower().startswith("win")


def run_subprocess(cmd, cwd=None, timeout=300):
    """
    Ejecuta un comando seguro (lista) y devuelve (ok, stdout, stderr, returncode).
    Nunca usar shell=True con comandos construidos dinámicamente.
    """
    try:
        # Asegurarse de que cmd sea lista
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
    """
    Hilo para ejecutar build y deploy sin bloquear la UI.
    Emite logs (texto), progreso (0-100) y finished_signal(exito:bool, mensaje:str).
    """
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, project_path, deploy_config=None):
        super().__init__()
        self.requested_path = project_path or os.getcwd()
        self.deploy_config = deploy_config or {}

        # Rutas candidatas para buscar el proyecto React
        self.possible_paths = [
            self.requested_path,
            os.path.join(self.requested_path, "turismo-frontend"),
            os.path.join(self.requested_path, "frontend"),
            os.path.join(self.requested_path, "src"),
        ]

        self.project_root = self.find_project_root()
        self.dist_path = os.path.join(self.project_root, "dist") if self.project_root else None

        # Intentar localizar backend Flask para integración
        self.backend_path = self.find_backend_path()
        # ✅ CORREGIDO: react-build -> build para Flask estándar
        self.react_build_dest = os.path.join(self.backend_path, "build") if self.backend_path else None

        # Rutas de node/npm (pueden ser 'node'/'npm' si están en PATH)
        self.npm_cmd = self.find_npm()
        self.node_cmd = self.find_node()

        # Estado interno
        self._stopped = False

    # -------------------------
    # UTILIDADES DE LOG
    # -------------------------
    def log(self, mensaje, nivel="INFO"):
        """Formatea y emite logs"""
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        texto = f"[{ts}] [{nivel}] {mensaje}"
        self.log_signal.emit(texto)

    # -------------------------
    # DETECCIÓN RUTAS
    # -------------------------
    def find_project_root(self):
        """Buscar carpeta donde exista package.json"""
        # ✅ RUTAS ACTUALIZADAS para tu estructura de proyecto
        posibles_rutas = [
            self.requested_path,
            os.path.join(self.requested_path, "frontend"),
            os.path.join(self.requested_path, "turismo-frontend"),
            os.path.join(self.requested_path, "src"),
            # Rutas específicas para tu proyecto
            r"E:\Sistemas de app para androide\turismo-app\frontend",
            r"E:\Sistemas de app para androide\frontend",
            os.path.join(os.path.dirname(self.requested_path), "frontend"),
            os.path.join(os.path.dirname(os.path.dirname(self.requested_path)), "frontend"),
        ]
        
        for ruta in posibles_rutas:
            try:
                ruta_abs = os.path.abspath(ruta)
                package_json = os.path.join(ruta_abs, "package.json")
                self.log(f"Buscando package.json en: {ruta_abs}", "DEBUG")
                
                if os.path.exists(package_json):
                    self.log(f"✅ Encontrado package.json en: {ruta_abs}")
                    return ruta_abs
            except Exception as e:
                self.log(f"Error comprobando {ruta}: {e}", "DEBUG")
        
        # ✅ SI NO ENCUENTRA, MOSTRAR RUTAS DISPONIBLES
        self.log("❌ No se encontró package.json. Rutas disponibles:", "ERROR")
        for ruta in posibles_rutas:
            ruta_abs = os.path.abspath(ruta)
            existe = os.path.exists(ruta_abs)
            self.log(f"   {'✅' if existe else '❌'} {ruta_abs}")
        
        return None
    
    def find_backend_path(self):
        """Intentar localizar backend Flask (api.py) en rutas probables"""
        posibles = [
            os.path.join(self.requested_path, "turismo-backend"),
            os.path.join(os.path.dirname(self.requested_path), "turismo-backend"),
            os.path.join(self.requested_path, "backend"),
            os.path.join(self.requested_path, "turismo-app", "turismo-backend"),
            # rutas absolutas comunes - puedes personalizarlas
            r"E:\Sistemas de app para androide\turismo-app\turismo-backend",
            r"E:\Sistemas de app para androide\turismo-backend",
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
        self.log("npm no encontrado en el sistema PATH o rutas comunes.", "WARN")
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
        self.log("node no encontrado en el sistema PATH o rutas comunes.", "WARN")
        return None

    # -------------------------
    # VERIFICACIONES
    # -------------------------
    def verify_environment(self):
        """Verificar que lo mínimo esté presente"""
        if not self.project_root:
            raise RuntimeError("No se encontró la raíz del proyecto (package.json).")
        if not self.node_cmd or not self.npm_cmd:
            raise RuntimeError("Node.js o npm no están instalados / no están en PATH.")
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
            # Mostrar algunos mensajes útiles del output si existen
            if out:
                for l in out.splitlines()[-8:]:
                    self.log(l, "DEBUG")
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
        # Asegurarnos de usar npm_cmd con run build
        ok, out, err, rc = run_subprocess([self.npm_cmd, "run", "build"], cwd=self.project_root, timeout=900)
        if ok:
            self.log("Build completado correctamente")
            # Info de tamaño y archivos
            if os.path.exists(self.dist_path):
                size = self.get_folder_size(self.dist_path)
                self.log(f"Carpeta dist creada: {self.dist_path} (tamaño: {size})")
            return True
        else:
            self.log(f"Error ejecutando build: {err[:2000] or out[:2000]}", "ERROR")
            return False

    # -------------------------
    # COPIAR BUILD A FLASK
    # -------------------------
    def copy_build_to_flask(self):
        """Copia dist -> backend/build limpiando destino previo"""
        if not self.backend_path:
            self.log("No hay backend configurado; se omite integración Flask", "INFO")
            return False

        if not self.dist_path or not os.path.exists(self.dist_path):
            self.log("No se encontró la carpeta dist; asegúrate de que el build se generó correctamente.", "ERROR")
            return False

        destino = self.react_build_dest
        try:
            if os.path.exists(destino):
                self.log(f"Limpiando destino anterior: {destino}")
                shutil.rmtree(destino, ignore_errors=True)
                time.sleep(0.2)

            self.log(f"Copiando build desde {self.dist_path} -> {destino}")
            shutil.copytree(self.dist_path, destino)
            size = self.get_folder_size(destino)
            self.log(f"Build copiado al backend: {destino} (tamaño: {size})")
            
            # ✅ CORREGIDO: Verificar archivos críticos para Flask
            existentes = os.listdir(destino)
            checks = []
            for crit in ("index.html", "assets", "static"):
                checks.append((crit, crit in existentes or any(x.startswith(crit) for x in existentes)))
            for crit, ok in checks:
                self.log(f"{'✅' if ok else '⚠️'} {crit} {'encontrado' if ok else 'no encontrado'}", "DEBUG")
            
            # ✅ AGREGADO: Actualizar Flask para servir build
            self.update_flask_for_build()
            
            return True
        except Exception as e:
            self.log(f"Error copiando build a Flask: {e}", "ERROR")
            return False

    def update_flask_for_build(self):
        """Actualizar Flask para servir el build de React"""
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
            
            # Verificar si ya tiene la configuración para servir build
            if 'static_folder=' in contenido and 'build' in contenido:
                self.log("Flask ya configurado para servir build", "DEBUG")
                return
            
            # Buscar la línea de creación de la app Flask
            lines = contenido.split('\n')
            updated_lines = []
            app_created = False
            
            for line in lines:
                updated_lines.append(line)
                # Buscar donde se crea la app Flask
                if 'Flask(' in line and 'app =' in line and not app_created:
                    # Agregar configuración para servir build
                    updated_lines.append('')
                    updated_lines.append('# ✅ Configuración para servir build de React')
                    updated_lines.append('app.static_folder = os.path.join(os.path.dirname(__file__), "build")')
                    updated_lines.append('app.static_url_path = ""')
                    updated_lines.append('')
                    app_created = True
            
            # Si no se encontró donde insertar, agregar al final del archivo
            if not app_created:
                updated_lines.append('')
                updated_lines.append('# ✅ Configuración para servir build de React')
                updated_lines.append('app.static_folder = os.path.join(os.path.dirname(__file__), "build")')
                updated_lines.append('app.static_url_path = ""')
            
            # Escribir archivo actualizado
            with open(api_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(updated_lines))
            
            self.log("✅ Flask actualizado para servir build de React", "INFO")
            
        except Exception as e:
            self.log(f"⚠️  No se pudo actualizar Flask automáticamente: {e}", "WARN")

    # -------------------------
    # DEPLOYS
    # -------------------------
    def deploy_via_railway(self):
        """Deploy automático con railway CLI"""
        self.log("Intentando deploy a Railway (railway deploy)...")
        ok, out, err, rc = run_subprocess(["railway", "--version"], timeout=12)
        if not ok:
            self.log("Railway CLI no está instalado. Instalalo con: npm i -g @railway/cli", "WARN")
            return True  # no es crítico para terminar; build ya hecho

        # Ejecutar deploy
        ok, out, err, rc = run_subprocess(["railway", "deploy"], cwd=self.project_root, timeout=1200)
        if ok:
            self.log("Deploy a Railway completado")
            return True
        else:
            self.log(f"Railway deploy falló: {err[:800] or out[:800]}", "WARN")
            return True  # no fatal, sugerimos revisar logs

    def deploy_github_pages(self):
        """Deploy usando gh-pages (npm run deploy) si está configurado"""
        self.log("Intentando deploy a GitHub Pages (si está configurado)...")
        # Si gh-pages está en package.json scripts, intentar npm run deploy
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
                    else:
                        self.log("Error en deploy gh-pages: " + (err or out)[:1000], "WARN")
                        return True
        except Exception as e:
            self.log(f"Error comprobando package.json para gh-pages: {e}", "WARN")
        # Sugerir instrucciones manuales
        self.log("gh-pages no configurado o deploy automático falló. Usar instrucciones manuales.", "INFO")
        return True

    def deploy_netlify(self):
        self.log("Instrucciones Netlify: arrastrar carpeta dist o conectar repo GitHub.")
        return True

    def deploy_vercel(self):
        self.log("Instrucciones Vercel: instalar Vercel CLI y ejecutar `vercel --prod` o conectar repo.")
        return True

    def deploy_generic(self):
        self.log("Deploy genérico: subir carpeta 'dist' al servidor (FTP/SCP) o configurar CI/CD", "INFO")
        return True

    def perform_deploy(self):
        """Decidir y ejecutar el deploy basado en deploy_config/base_url"""
        base_url = (self.deploy_config or {}).get("base_url", "") if self.deploy_config else ""
        if not base_url:
            self.log("No hay base_url configurada: se omitirá el deploy automático (solo build).", "INFO")
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
            # Si contiene 'ssh' o 'ftp' podríamos implementar lógica adicional
            return self.deploy_generic()

    # -------------------------
    # VERIFICACIÓN POST-DEPLOY
    # -------------------------
    def verify_production(self):
        """Comprobar endpoints básicos (si requests está disponible y base_url existe)"""
        if not requests:
            self.log("requests no está instalado: no puedo verificar endpoints HTTP.", "WARN")
            return True

        base_url = (self.deploy_config or {}).get("base_url", "")
        if not base_url:
            self.log("No hay base_url para verificación.", "DEBUG")
            return True

        # ✅ CORREGIDO: Endpoints actualizados para tu API
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
        """Secuencia principal: verificar -> deps -> build -> copiar -> deploy -> verificar"""
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
                self.log("No se detectaron node_modules; se instalarán dependencias...")
                if not self.install_dependencies():
                    self.finished_signal.emit(False, "Error instalando dependencias. Revisá los logs.")
                    return

            self.progress_signal.emit(18)

            # 3) Ejecutar build
            if not self.run_build():
                self.finished_signal.emit(False, "Error en el build. Revisá los logs.")
                return

            self.progress_signal.emit(70)

            # 4) Integrar con Flask (copiar dist)
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

            # 5) Ejecutar deploy (si corresponde)
            deploy_ok = self.perform_deploy()
            if deploy_ok:
                self.progress_signal.emit(92)
            else:
                self.progress_signal.emit(85)

            # 6) Verificación final (ping a endpoints)
            try:
                ok_prod = self.verify_production()
                if ok_prod:
                    self.progress_signal.emit(97)
                    self.log("Verificación final OK", "INFO")
                else:
                    self.log("Algunos endpoints no respondieron correctamente", "WARN")
            except Exception as e:
                self.log(f"Error en verificación final: {e}", "WARN")

            # Mensaje final
            final_msg = "Build & Deploy completado"
            if integrated:
                final_msg += " + Integración Flask realizada"
            else:
                final_msg += " (sin integración Flask)" if self.backend_path else " (no se integró con Flask)"

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
    """Diálogo para build y deploy automático - CON FLASK INTEGRADO"""
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

        # Estado inicial
        self.verify_system()

    # -------------------------
    # LOG UI
    # -------------------------
    def append_log(self, mensaje):
        """Agregar mensaje al QTextEdit (desde señales)"""
        self.log_output.append(mensaje)
        self.log_output.moveCursor(self.log_output.textCursor().End)

    def clear_log(self):
        self.log_output.clear()
        self.append_log("🗑️ Log limpiado")

    # -------------------------
    # CARGAR CONFIG DB
    # -------------------------
    def load_config_from_db(self):
        """Cargar configuración de deploy desde la BD local si está"""
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

    # -------------------------
    # VERIFICACIONES LOCALES
    # -------------------------
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

    # -------------------------
    # INICIAR PROCESO
    # -------------------------
    def start_process(self, deploy_cfg):
        """Inicia hilo de build/deploy"""
        self.btn_build_only.setEnabled(False)
        self.btn_build_deploy.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_output.clear()
        self.append_log("🚀 INICIANDO PROCESO BUILD & DEPLOY...")

        # Preparar configuración
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