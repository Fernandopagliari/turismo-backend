# backend_deploy.py - VERSIÓN LIMPIA ADAPTADA A VITE
# -*- coding: utf-8 -*-

import os
import subprocess
import time
import platform
import requests

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QProgressBar, QMessageBox,
    QGroupBox, QComboBox, QLineEdit, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal


# ==========================================================
# THREAD PRINCIPAL DE DEPLOY
# ==========================================================

class BackendDeployThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, backend_path, servidor_config):
        super().__init__()
        self.backend_path = backend_path
        self.servidor_config = servidor_config or {}
        self.datos_hosting = self.servidor_config.get("datos_hosting", {})

    # ------------------------------------------------------
    # UTILIDADES
    # ------------------------------------------------------

    def log(self, msg):
        self.log_signal.emit(msg)

    def verificar_herramienta(self, nombre):
        try:
            subprocess.run(
                [nombre, "--version"],
                capture_output=True,
                shell=True,
                timeout=5
            )
            return True
        except Exception:
            return False

    def es_repo_git(self):
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.backend_path,
                capture_output=True,
                text=True,
                shell=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def tiene_remote(self):
        try:
            result = subprocess.run(
                ["git", "remote"],
                cwd=self.backend_path,
                capture_output=True,
                text=True,
                shell=True
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    # ------------------------------------------------------
    # VALIDACIONES VITE
    # ------------------------------------------------------

    def validar_dist_vite(self):
        dist_path = os.path.join(self.backend_path, "dist")
        index_path = os.path.join(dist_path, "index.html")

        if not os.path.exists(dist_path):
            self.log("❌ No existe la carpeta dist/")
            return False

        if not os.path.exists(index_path):
            self.log("❌ dist/index.html no encontrado (Vite no construido)")
            return False

        self.log("✅ dist/ de Vite detectado correctamente")
        return True

    # ------------------------------------------------------
    # DEPLOY
    # ------------------------------------------------------

    def deploy_git(self):
        try:
            os.chdir(self.backend_path)

            self.log("🔄 Sincronizando con repositorio...")
            subprocess.run(["git", "pull"], shell=True)

            archivos = ["api.py", "requirements.txt", "Procfile", "dist", "static"]
            for item in archivos:
                if os.path.exists(item):
                    subprocess.run(["git", "add", item], shell=True)

            commit_msg = f"DEPLOY VITE {time.strftime('%Y-%m-%d %H:%M')} - {platform.node()}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                capture_output=True,
                text=True,
                shell=True
            )

            if result.returncode == 0:
                self.log("✅ Commit realizado")
                subprocess.run(["git", "push"], shell=True)
                self.log("🚀 Push a remoto exitoso")
            else:
                self.log("ℹ️ No había cambios para commitear")

            return True

        except Exception as e:
            self.log(f"❌ Error en deploy Git: {e}")
            return False

    def deploy_manual(self):
        self.log("📋 DEPLOY MANUAL")
        self.log("Subir los siguientes archivos al hosting:")
        self.log("• api.py")
        self.log("• requirements.txt")
        self.log("• Procfile")
        self.log("• dist/ (build Vite)")
        self.log("• static/assets/imagenes/")
        return True

    # ------------------------------------------------------
    # RUN
    # ------------------------------------------------------

    def run(self):
        try:
            self.log("🚀 INICIANDO DEPLOY BACKEND (VITE)")
            self.progress_signal.emit(10)

            if not self.validar_dist_vite():
                self.finished_signal.emit(False, "❌ Build de Vite inválido")
                return

            self.progress_signal.emit(30)

            git_ok = self.verificar_herramienta("git")
            repo_ok = self.es_repo_git()
            remote_ok = self.tiene_remote()

            if git_ok and repo_ok and remote_ok:
                self.log("🎯 Modo Git detectado")
                ok = self.deploy_git()
            else:
                self.log("⚠️ Usando modo manual")
                ok = self.deploy_manual()

            self.progress_signal.emit(100)

            if ok:
                self.finished_signal.emit(True, "✅ Deploy backend completado")
            else:
                self.finished_signal.emit(False, "❌ Falló el deploy")

        except Exception as e:
            self.finished_signal.emit(False, f"❌ Error crítico: {e}")


# ==========================================================
# DIÁLOGO UI
# ==========================================================

class DialogoBackendDeploy(QDialog):

    def __init__(self, parent=None, backend_path=None):
        super().__init__(parent)
        self.backend_path = backend_path or os.getcwd()
        self.datos_hosting = {}
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("🚀 Deploy Backend (Vite)")
        self.setMinimumSize(800, 550)

        layout = QVBoxLayout(self)

        titulo = QLabel("🚀 DEPLOY BACKEND – VITE + FLASK")
        titulo.setStyleSheet("font-size:16px;font-weight:bold;")
        layout.addWidget(titulo)

        grupo = QGroupBox("Configuración")
        gl = QVBoxLayout(grupo)

        self.combo = QComboBox()
        self.combo.addItems(["Automático", "Git", "Manual"])
        gl.addWidget(self.combo)

        layout.addWidget(grupo)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        botones = QHBoxLayout()
        self.btn_deploy = QPushButton("🚀 Deploy")
        self.btn_deploy.clicked.connect(self.iniciar_deploy)
        botones.addWidget(self.btn_deploy)

        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.close)
        botones.addWidget(cerrar)

        layout.addLayout(botones)

    def iniciar_deploy(self):
        self.log_output.clear()
        self.progress.setValue(0)

        self.thread = BackendDeployThread(
            backend_path=self.backend_path,
            servidor_config={"datos_hosting": self.datos_hosting}
        )

        self.thread.log_signal.connect(self.log)
        self.thread.progress_signal.connect(self.progress.setValue)
        self.thread.finished_signal.connect(self.finalizado)
        self.thread.start()

    def log(self, msg):
        self.log_output.append(msg)
        QApplication.processEvents()

    def finalizado(self, ok, msg):
        if ok:
            QMessageBox.information(self, "Deploy", msg)
        else:
            QMessageBox.critical(self, "Deploy", msg)


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":
    app = QApplication([])
    dlg = DialogoBackendDeploy()
    dlg.show()
    app.exec_()
