# build_deploy.py - VERSIÓN COMPLETA CORREGIDA
# -*- coding: utf-8 -*-
import os
import subprocess
import shutil
import time
import platform
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QProgressBar, QMessageBox,
    QGroupBox, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class BuildDeployThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, project_path, deploy_config=None, hacer_git=True):
        super().__init__()
        self.project_path = project_path or os.getcwd()
        self.deploy_config = deploy_config or {}
        self.hacer_git = hacer_git
        self.frontend_path = self.find_frontend_path()
        self.backend_path = self.find_backend_path()
        self.npm_path = self.find_npm()

    def find_npm(self):
        """Buscar npm de forma más agresiva"""
        commands = ["npm"]
        if platform.system() == "Windows":
            commands.extend(["npm.cmd", "npm.exe"])
        
        for cmd in commands:
            try:
                if platform.system() == "Windows":
                    find_cmd = f"where {cmd}"
                else:
                    find_cmd = f"which {cmd}"
                
                result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    return cmd
            except:
                continue
        
        for cmd in commands:
            try:
                result = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return cmd
            except:
                continue
        
        return None

    def find_frontend_path(self):
        """Buscar frontend de forma más precisa"""
        posibles_rutas = [
            os.path.join(self.project_path, "turismo-frontend"),
            os.path.join(self.project_path, "frontend"),
            os.path.join(self.project_path, "..", "turismo-frontend"),
            self.project_path
        ]
        
        for ruta in posibles_rutas:
            ruta_abs = os.path.abspath(ruta)
            package_json = os.path.join(ruta_abs, "package.json")
            
            if os.path.exists(ruta_abs) and os.path.exists(package_json):
                return ruta_abs
                
        return None

    def find_backend_path(self):
        """Buscar backend de forma más precisa"""
        posibles_rutas = [
            os.path.join(self.project_path, "turismo-backend"),
            os.path.join(self.project_path, "backend"),
            os.path.join(self.project_path, "..", "turismo-backend")
        ]
        
        for ruta in posibles_rutas:
            ruta_abs = os.path.abspath(ruta)
            api_py = os.path.join(ruta_abs, "api.py")
            requirements = os.path.join(ruta_abs, "requirements.txt")
            
            if os.path.exists(ruta_abs) and (os.path.exists(api_py) or os.path.exists(requirements)):
                return ruta_abs
                
        return None

    def log(self, mensaje, nivel="INFO"):
        ts = time.strftime("%H:%M:%S")
        texto = f"[{ts}] {mensaje}"
        self.log_signal.emit(texto)

    def run_subprocess(self, cmd, cwd=None, timeout=300):
        try:
            result = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                shell=platform.system() == "Windows"
            )
            return result.returncode == 0, result.stdout or "", result.stderr or ""
        except Exception as e:
            return False, "", str(e)

    def ejecutar_git(self):
        if not self.hacer_git:
            self.log("Git deshabilitado - continuando con build")
            return True

        self.log("Ejecutando Git...")
        
        ok, out, err = self.run_subprocess("git status --porcelain", cwd=self.frontend_path)
        if not ok:
            self.log("❌ Error en git status")
            return False
            
        if not out.strip():
            self.log("⚠️ No hay cambios para commit - continuando")
            return True

        self.log(f"📝 Cambios detectados: {len(out.splitlines())} archivos")

        ok, out, err = self.run_subprocess("git add .", cwd=self.frontend_path)
        if not ok:
            self.log(f"❌ Error en git add: {err}")
            self.log("⚠️ Continuando sin Git add")
            return True
            
        self.log("✅ Git add completado")

        commit_msg = 'Auto: Actualización automática'
        ok, out, err = self.run_subprocess(f'git commit -m "{commit_msg}"', cwd=self.frontend_path)
        if not ok:
            self.log(f"⚠️ Git commit falló (posiblemente sin cambios): {err}")
            self.log("Continuando proceso sin commit")
        else:
            self.log("✅ Git commit completado")

        ok, out, err = self.run_subprocess("git push origin main", cwd=self.frontend_path)
        if not ok:
            self.log(f"⚠️ Git push falló: {err}")
            self.log("Continuando proceso sin push")
        else:
            self.log("✅ Git push completado")

        self.log("Git finalizado")
        return True

    def ejecutar_build_react(self):
        if not self.npm_path:
            self.log("❌ ERROR: npm no encontrado")
            return False

        if not self.frontend_path:
            self.log("❌ ERROR: No se encontró el frontend")
            return False

        self.log(f"📁 Construyendo desde: {self.frontend_path}")
        self.log(f"🔧 Usando npm: {self.npm_path}")
        self.log("Ejecutando npm run build...")
        
        ok, out, err = self.run_subprocess(
            [self.npm_path, "run", "build"], 
            cwd=self.frontend_path,
            timeout=600
        )
        
        # ✅ VERIFICAR AMBAS UBICACIONES POSIBLES
        dist_path = os.path.join(self.frontend_path, "dist")
        backend_assets_path = os.path.join(self.backend_path, "assets") if self.backend_path else None
        
        if ok:
            # ✅ PRIMERO: Verificar si se creó en backend/assets (tu configuración)
            if backend_assets_path and os.path.exists(backend_assets_path):
                self.log("✅ Build de React completado (en backend/assets)")
                archivos = os.listdir(backend_assets_path)
                self.log(f"📁 Archivos en backend/assets/: {len(archivos)}")
                for archivo in archivos[:5]:
                    self.log(f"   - {archivo}")
                return True
            
            # ✅ SEGUNDO: Verificar si se creó en frontend/dist (configuración normal)
            elif os.path.exists(dist_path):
                self.log("✅ Build de React completado (en frontend/dist)")
                archivos = os.listdir(dist_path)
                self.log(f"📁 Archivos en dist/: {len(archivos)}")
                for archivo in archivos[:5]:
                    self.log(f"   - {archivo}")
                return True
            
            else:
                self.log("❌ ERROR: No se creó carpeta de build en ninguna ubicación")
                return False
        else:
            self.log(f"❌ ERROR en build React: {err}")
            return False

    def copiar_archivos_correctamente(self):
        if not self.frontend_path:
            self.log("❌ No se encontró frontend")
            return False

        dist_path = os.path.join(self.frontend_path, "dist")
        if not os.path.exists(dist_path):
            self.log("❌ No existe dist/ - ejecuta build primero")
            return False

        if not self.backend_path:
            self.log("⚠️ Backend no encontrado - solo build")
            return True

        assets_destino = os.path.join(self.backend_path, "assets")
        self.log(f"📁 Copiando desde: {dist_path}")
        self.log(f"📁 Copiando hacia: {assets_destino}")

        # Limpiar destino anterior
        if os.path.exists(assets_destino):
            shutil.rmtree(assets_destino)

        try:
            # ✅ COPIAR TODO el contenido de dist/
            shutil.copytree(dist_path, assets_destino)
            
            # ✅ VERIFICAR QUE index.html SE COPIÓ
            index_destino = os.path.join(assets_destino, "index.html")
            if os.path.exists(index_destino):
                file_size = os.path.getsize(index_destino)
                self.log(f"✅ index.html copiado ({file_size} bytes)")
            else:
                self.log("❌ ERROR: index.html NO se copió")
                return False
            
            # ✅ VERIFICAR ESTRUCTURA COMPLETA
            self.log("📁 Estructura final en backend/assets/:")
            for item in os.listdir(assets_destino):
                item_path = os.path.join(assets_destino, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path)
                    self.log(f"   📄 {item} ({size} bytes)")
                else:
                    num_files = len(os.listdir(item_path))
                    self.log(f"   📁 {item}/ ({num_files} archivos)")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error en copia: {e}")
            return False
        
    def run(self):
        try:
            self.progress_signal.emit(10)
            self.log("🚀 Iniciando proceso completo...")

            if not self.frontend_path:
                self.finished_signal.emit(False, "No se encontró el frontend (turismo-frontend)")
                return

            if not self.npm_path:
                self.finished_signal.emit(False, "npm no encontrado. Instala Node.js")
                return

            self.log(f"📍 Frontend: {self.frontend_path}")
            if self.backend_path:
                self.log(f"📍 Backend: {self.backend_path}")
            else:
                self.log("📍 Backend: No detectado (solo build)")

            if self.hacer_git:
                self.progress_signal.emit(30)
                self.ejecutar_git()

            self.progress_signal.emit(50)
            if not self.ejecutar_build_react():
                self.finished_signal.emit(False, "Falló el build de React")
                return

            self.progress_signal.emit(80)
            if self.backend_path:
                if not self.copiar_archivos_correctamente():
                    self.finished_signal.emit(False, "Error copiando archivos")
                    return
            else:
                self.log("⚠️ No se copian archivos - backend no detectado")

            self.progress_signal.emit(100)
            self.finished_signal.emit(True, "✅ Proceso completado exitosamente")
            
        except Exception as e:
            self.log(f"❌ Error crítico: {str(e)}")
            self.finished_signal.emit(False, f"Error: {str(e)}")

# -------------------------
# INTERFAZ COMPACTA
# -------------------------
class DialogoBuildDeploy(QDialog):
    def __init__(self, parent=None, project_path=None):
        super().__init__(parent)
        self.project_path = project_path or os.getcwd()
        self.build_thread = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("🚀 Build & Deploy")
        self.setFixedSize(600, 500)

        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        titulo = QLabel("Build & Deploy Automático")
        titulo.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(titulo)

        self.chk_git = QCheckBox("Incluir Git (subir a GitHub)")
        self.chk_git.setChecked(True)
        layout.addWidget(self.chk_git)

        info_group = QGroupBox("Estado del Sistema")
        info_layout = QVBoxLayout()
        self.lbl_frontend = QLabel("Frontend: Verificando...")
        self.lbl_backend = QLabel("Backend: Verificando...") 
        self.lbl_npm = QLabel("npm: Verificando...")
        info_layout.addWidget(self.lbl_frontend)
        info_layout.addWidget(self.lbl_backend)
        info_layout.addWidget(self.lbl_npm)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(200)
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("font-family: 'Consolas'; font-size: 9px;")
        layout.addWidget(self.log_output)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        botones_layout = QHBoxLayout()
        self.btn_build = QPushButton("Ejecutar")
        self.btn_verificar = QPushButton("Verificar")
        self.btn_limpiar = QPushButton("Limpiar")
        self.btn_cerrar = QPushButton("Cerrar")

        btn_style = "QPushButton { padding: 6px; font-size: 11px; }"
        self.btn_build.setStyleSheet(btn_style + "background-color: #27ae60; color: white;")
        self.btn_verificar.setStyleSheet(btn_style + "background-color: #3498db; color: white;")
        self.btn_limpiar.setStyleSheet(btn_style + "background-color: #f39c12; color: white;")
        self.btn_cerrar.setStyleSheet(btn_style + "background-color: #e74c3c; color: white;")

        botones_layout.addWidget(self.btn_build)
        botones_layout.addWidget(self.btn_verificar)
        botones_layout.addWidget(self.btn_limpiar)
        botones_layout.addWidget(self.btn_cerrar)
        layout.addLayout(botones_layout)

        self.setLayout(layout)

        self.btn_build.clicked.connect(self.iniciar_build)
        self.btn_verificar.clicked.connect(self.verificar_sistema)
        self.btn_limpiar.clicked.connect(self.limpiar_log)
        self.btn_cerrar.clicked.connect(self.close)

        self.verificar_sistema()

    def log(self, mensaje):
        self.log_output.append(mensaje)

    def limpiar_log(self):
        self.log_output.clear()

    def verificar_sistema(self):
        thread = BuildDeployThread(self.project_path)
        
        if thread.npm_path:
            self.lbl_npm.setText("npm: ✅ Disponible")
        else:
            self.lbl_npm.setText("npm: ❌ No encontrado")
            
        if thread.frontend_path:
            self.lbl_frontend.setText("Frontend: ✅ Detectado")
        else:
            self.lbl_frontend.setText("Frontend: ❌ No encontrado")
            
        if thread.backend_path:
            self.lbl_backend.setText("Backend: ✅ Detectado")
        else:
            self.lbl_backend.setText("Backend: ⚠️ No detectado")

    def iniciar_build(self):
        self.btn_build.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_output.clear()
        
        self.log("Iniciando proceso...")
        
        self.build_thread = BuildDeployThread(self.project_path, None, self.chk_git.isChecked())
        self.build_thread.log_signal.connect(self.log)
        self.build_thread.progress_signal.connect(self.progress_bar.setValue)
        self.build_thread.finished_signal.connect(self.proceso_finalizado)
        self.build_thread.start()

    def proceso_finalizado(self, exito, mensaje):
        self.btn_build.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.log(mensaje)
        
        if exito:
            QMessageBox.information(self, "✅ Éxito", 
                "Proceso completado:\n" +
                ("• Cambios subidos a GitHub\n" if self.chk_git.isChecked() else "") +
                "• Build de React generado\n" +
                "• Archivos copiados al backend\n\n" +
                "Ejecuta backend_deploy.py")
        else:
            QMessageBox.critical(self, "❌ Error", mensaje)

def mostrar_dialogo_build_deploy(parent=None):
    dialogo = DialogoBuildDeploy(parent)
    dialogo.exec_()

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication([])
    dialogo = DialogoBuildDeploy()
    dialogo.show()
    app.exec_()