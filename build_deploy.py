# build_deploy.py - VERSIÓN COORDINADA PARA RENDER + MULTI-MÁQUINA
# -*- coding: utf-8 -*-

import os
import subprocess
import shutil
import time
import platform

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QPushButton, QTextEdit, QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal


# ============================================================
# THREAD PRINCIPAL
# ============================================================
class BuildDeployThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, project_path, deploy_config=None, hacer_git=True):
        super().__init__()
        self.project_path = project_path or os.getcwd()
        self.deploy_config = deploy_config or {}
        self.hacer_git = hacer_git

        self.frontend_path = self.find_frontend_path()
        self.backend_path = self.find_backend_path()
        self.npm_path = self.find_npm()
        self.git_disponible = self.verificar_git()

    # --------------------------------------------------------
    def log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.log_signal.emit(f"[{ts}] {msg}")

    def run_cmd(self, cmd, cwd=None):
        r = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=platform.system() == "Windows"
        )
        return r.returncode == 0, r.stdout, r.stderr

    def verificar_git(self):
        ok, _, _ = self.run_cmd(["git", "--version"])
        return ok

    # --------------------------------------------------------
    # DETECCIÓN
    # --------------------------------------------------------
    def find_npm(self):
        for cmd in ["npm", "npm.cmd", "npm.exe"]:
            ok, _, _ = self.run_cmd([cmd, "--version"])
            if ok:
                return cmd
        return None

    def find_frontend_path(self):
        for r in [
            os.path.join(self.project_path, "turismo-frontend"),
            os.path.join(self.project_path, "frontend"),
            self.project_path
        ]:
            if os.path.exists(os.path.join(r, "package.json")):
                return os.path.abspath(r)
        return None

    def find_backend_path(self):
        for r in [
            os.path.join(self.project_path, "turismo-backend"),
            os.path.join(self.project_path, "backend"),
            self.project_path
        ]:
            if os.path.exists(os.path.join(r, "api.py")):
                self.log(f"📍 Backend detectado en {r}")
                return os.path.abspath(r)
        return None

    # --------------------------------------------------------
    # BUILD REACT
    # --------------------------------------------------------
    def build_react(self):
        if not self.frontend_path or not self.npm_path:
            self.log("❌ Frontend o npm no encontrado")
            return False

        dist = os.path.join(self.frontend_path, "dist")

        if os.path.exists(dist):
            self.log("🧹 Limpiando dist anterior")
            shutil.rmtree(dist)

        self.log("⚙️ npm run build")
        ok, out, err = self.run_cmd(
            [self.npm_path, "run", "build"],
            cwd=self.frontend_path
        )

        if not ok:
            self.log(err)
            return False

        self.log("✅ Build React OK")
        return True

    # --------------------------------------------------------
    # COPIAR DIST → BACKEND
    # --------------------------------------------------------
    def copy_dist_to_backend(self):
        if not self.backend_path:
            return True

        src = os.path.join(self.frontend_path, "dist")
        dst = os.path.join(self.backend_path, "dist")

        if os.path.exists(dst):
            shutil.rmtree(dst)

        shutil.copytree(src, dst)
        self.log("📦 dist copiado a backend")
        return True

    # --------------------------------------------------------
    # GIT ROBUSTO (CLAVE PARA RENDER)
    # --------------------------------------------------------
    def git_backend_safe(self):
        if not self.git_disponible or not self.hacer_git:
            return True

        self.log("🔄 Git pull --rebase")
        self.run_cmd("git pull --rebase origin main", cwd=self.backend_path)

        self.log("📦 git add")
        self.run_cmd("git add .", cwd=self.backend_path)

        self.log("📝 git commit")
        ok, out, err = self.run_cmd(
            f'git commit -m "AUTO DEPLOY {platform.node()} {time.strftime("%Y-%m-%d %H:%M")}"',
            cwd=self.backend_path
        )

        if not ok:
            self.log("⚠️ Sin cambios para commit")

        self.log("🚀 git push")
        ok, out, err = self.run_cmd("git push origin main", cwd=self.backend_path)

        if not ok:
            self.log(err)
            return False

        self.log("✅ Push OK → Render detectará cambios")
        return True

    # --------------------------------------------------------
    def run(self):
        self.log("🚀 Iniciando Build + Deploy")

        if not self.build_react():
            self.finished_signal.emit(False, "Falló build React")
            return

        if not self.copy_dist_to_backend():
            self.finished_signal.emit(False, "Falló copia dist")
            return

        if not self.git_backend_safe():
            self.finished_signal.emit(False, "Falló git push")
            return

        self.finished_signal.emit(True, "Deploy OK")


# ============================================================
# UI
# ============================================================
class DialogoBuildDeploy(QDialog):
    def __init__(self, parent=None, project_path=None):
        super().__init__(parent)
        self.project_path = project_path or os.getcwd()
        self.thread = None
        self.setWindowTitle("🚀 Build Deploy Render")
        self.setFixedSize(600, 500)

        layout = QVBoxLayout(self)

        self.log = QTextEdit(readOnly=True)
        layout.addWidget(self.log)

        btn = QPushButton("🚀 Ejecutar Deploy")
        btn.clicked.connect(self.start)
        layout.addWidget(btn)

    def start(self):
        self.log.clear()
        self.thread = BuildDeployThread(self.project_path)
        self.thread.log_signal.connect(self.log.append)
        self.thread.finished_signal.connect(self.on_finished)
        self.thread.start()

    

    def on_finished(self, ok, msg):
        QMessageBox.information(self, "Resultado", msg)



def mostrar_dialogo_build_deploy(parent=None):
    dlg = DialogoBuildDeploy(parent)
    dlg.exec_()


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication([])
    mostrar_dialogo_build_deploy()
    app.exec_()
