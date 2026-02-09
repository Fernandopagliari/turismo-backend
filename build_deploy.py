# build_deploy.py - VERSIÓN COORDINADA PARA MÚLTIPLES MÁQUINAS
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


# ============================================================
# THREAD PRINCIPAL DE BUILD + DEPLOY
# ============================================================
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

        self.git_disponible = self.verificar_git_disponible()

    # --------------------------------------------------------
    # UTILIDADES
    # --------------------------------------------------------
    def log(self, mensaje):
        ts = time.strftime("%H:%M:%S")
        self.log_signal.emit(f"[{ts}] {mensaje}")

    def run_subprocess(self, cmd, cwd=None, timeout=300):
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=platform.system() == "Windows"
            )
            return result.returncode == 0, result.stdout or "", result.stderr or ""
        except Exception as e:
            return False, "", str(e)

    def verificar_git_disponible(self):
        try:
            r = subprocess.run(["git", "--version"], capture_output=True, text=True)
            return r.returncode == 0
        except:
            return False

    # --------------------------------------------------------
    # DETECCIÓN DE ENTORNOS
    # --------------------------------------------------------
    def find_npm(self):
        comandos = ["npm"]
        if platform.system() == "Windows":
            comandos += ["npm.cmd", "npm.exe"]

        for cmd in comandos:
            try:
                r = subprocess.run([cmd, "--version"], capture_output=True, text=True)
                if r.returncode == 0:
                    return cmd
            except:
                pass
        return None

    def find_frontend_path(self):
        rutas = [
            os.path.join(self.project_path, "turismo-frontend"),
            os.path.join(self.project_path, "frontend"),
            self.project_path
        ]

        for r in rutas:
            if os.path.exists(os.path.join(r, "package.json")):
                return os.path.abspath(r)
        return None

    def find_backend_path(self):
        rutas = [
            os.path.join(self.project_path, "turismo-backend"),
            os.path.join(self.project_path, "backend"),
            self.project_path
        ]

        for r in rutas:
            if os.path.exists(os.path.join(r, "api.py")):
                self.log(f"📍 Backend detectado en {r}")
                return os.path.abspath(r)
        return None

    # --------------------------------------------------------
    # BUILD DE REACT
    # --------------------------------------------------------
    def ejecutar_build_react(self):
        if not self.npm_path or not self.frontend_path:
            self.log("❌ npm o frontend no disponible")
            return False

        dist = os.path.join(self.frontend_path, "dist")

        if os.path.exists(dist):
            self.log("🧹 Limpiando dist anterior")
            shutil.rmtree(dist)

        self.log("⚙️ Ejecutando npm run build")
        ok, out, err = self.run_subprocess(
            [self.npm_path, "run", "build"],
            cwd=self.frontend_path,
            timeout=600
        )

        if not ok:
            self.log(f"❌ Error build React: {err}")
            return False

        if not os.path.exists(os.path.join(dist, "index.html")):
            self.log("❌ dist/index.html NO encontrado")
            return False

        self.log("✅ Build React OK")
        return True

    # --------------------------------------------------------
    # COPIA FRONTEND → BACKEND (CLAVE PARA FLASK)
    # --------------------------------------------------------
    def copiar_archivos_correctamente(self):
        if not self.backend_path:
            self.log("⚠️ Backend no encontrado, solo build local")
            return True

        src = os.path.join(self.frontend_path, "dist")
        dst = os.path.join(self.backend_path, "dist")

        if not os.path.exists(os.path.join(src, "index.html")):
            self.log("❌ index.html no existe en frontend/dist")
            return False

        if os.path.exists(dst):
            self.log("🧹 Eliminando dist anterior en backend")
            shutil.rmtree(dst)

        shutil.copytree(src, dst)
        self.log("📦 dist copiado a backend correctamente")
        self.log("🌐 Flask servirá este dist como static root")

        return True

    # --------------------------------------------------------
    # GIT (SIN TOCAR LÓGICA ORIGINAL)
    # --------------------------------------------------------
    def ejecutar_git_seguro(self):
        if not self.git_disponible or not self.hacer_git:
            return True

        self.log("📦 Sincronizando frontend (dist)")
        self.run_subprocess("git add dist", cwd=self.frontend_path)
        self.run_subprocess(
            f'git commit -m "BUILD frontend {platform.node()} {time.strftime("%Y-%m-%d %H:%M")}"',
            cwd=self.frontend_path
        )
        self.run_subprocess("git push", cwd=self.frontend_path)
        return True

    def ejecutar_git_backend_seguro(self):
        if not self.git_disponible or not self.hacer_git:
            return True

        self.log("📦 Sincronizando backend (dist)")

        ok, out, err = self.run_subprocess(
            "git add dist api.py requirements.txt",
            cwd=self.backend_path
        )

        ok, out, err = self.run_subprocess(
            f'git commit -m "DEPLOY backend {platform.node()} {time.strftime("%Y-%m-%d %H:%M")}"',
            cwd=self.backend_path
        )

        if not ok:
            self.log("⚠️ No hubo cambios para commitear")
            self.log(err)

        ok, out, err = self.run_subprocess("git push", cwd=self.backend_path)

        if not ok:
            self.log(f"❌ Error en git push: {err}")
            return False

        return True


    # --------------------------------------------------------
    # FLUJO PRINCIPAL
    # --------------------------------------------------------
    def run(self):
        self.log("🚀 Iniciando Build + Deploy")

        if not self.ejecutar_build_react():
            self.finished_signal.emit(False, "Falló el build de React")
            return

        self.ejecutar_git_seguro()

        if not self.copiar_archivos_correctamente():
            self.finished_signal.emit(False, "Falló la copia a backend")
            return

        self.ejecutar_git_backend_seguro()

        self.log("✅ Deploy finalizado correctamente")
        self.finished_signal.emit(True, "Deploy completado con éxito")


# ============================================================
# DIÁLOGO UI
# ============================================================
class DialogoBuildDeploy(QDialog):
    def __init__(self, parent=None, project_path=None):
        super().__init__(parent)
        self.project_path = project_path or os.getcwd()
        self.build_thread = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("🚀 Build & Deploy Coordinado")
        self.setFixedSize(650, 520)

        layout = QVBoxLayout(self)

        self.log_output = QTextEdit(readOnly=True)
        layout.addWidget(self.log_output)

        btn = QPushButton("🚀 Ejecutar Deploy")
        btn.clicked.connect(self.iniciar)
        layout.addWidget(btn)

    def iniciar(self):
        self.log_output.clear()
        self.build_thread = BuildDeployThread(self.project_path)
        self.build_thread.log_signal.connect(self.log_output.append)
        self.build_thread.finished_signal.connect(self.finalizado)
        self.build_thread.start()

    def finalizado(self, ok, msg):
        QMessageBox.information(self, "Deploy", msg)


def mostrar_dialogo_build_deploy(parent=None):
    dlg = DialogoBuildDeploy(parent)
    dlg.exec_()


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication([])
    mostrar_dialogo_build_deploy()
    app.exec_()
