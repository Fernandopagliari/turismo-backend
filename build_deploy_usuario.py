# -*- coding: utf-8 -*-
"""
build_deploy_usuario.py
--------------------------------
Interfaz amigable en PyQt5 tipo Qt Designer
para realizar el proceso Build + Deploy
de una app React + Flask sin requerir conocimientos técnicos.
"""

import os
import sys
import shutil
import subprocess
import threading
import requests
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QProgressBar,
    QPushButton, QTextEdit, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import Qt

# -------------------------------
# CONFIGURACIÓN GENERAL
# -------------------------------
RUTA_PROYECTO = os.path.dirname(os.path.abspath(__file__))
RUTA_FRONTEND = os.path.join(RUTA_PROYECTO, "frontend")
RUTA_BACKEND = os.path.join(RUTA_PROYECTO, "backend", "static-assets")
RUTA_LOGS = os.path.join(RUTA_PROYECTO, "logs")
ARCHIVO_ENV = os.path.join(RUTA_PROYECTO, ".env")
ARCHIVO_LOG = os.path.join(RUTA_LOGS, "deploy.log")


# -------------------------------
# FUNCIONES AUXILIARES
# -------------------------------
def escribir_log(mensaje):
    """Guarda mensajes técnicos en logs/deploy.log"""
    if not os.path.exists(RUTA_LOGS):
        os.makedirs(RUTA_LOGS)
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensaje}\n")


def crear_env_si_no_existe():
    """Crea archivo .env con valores por defecto si no existe"""
    if not os.path.exists(ARCHIVO_ENV):
        with open(ARCHIVO_ENV, "w", encoding="utf-8") as f:
            f.write("MODO_DEPLOY=LOCAL\nURL_BACKEND=http://localhost:5000\n")
        escribir_log("Archivo .env creado automáticamente.")


def verificar_conexion_internet():
    """Comprueba conexión a internet"""
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except Exception:
        return False


def ejecutar_comando(comando, cwd):
    """Ejecuta comando y guarda salida"""
    try:
        resultado = subprocess.run(
            comando, cwd=cwd, shell=True,
            capture_output=True, text=True, encoding="utf-8"
        )
        escribir_log(resultado.stdout)
        escribir_log(resultado.stderr)
        return resultado.returncode == 0
    except Exception as e:
        escribir_log(f"Error ejecutando comando: {e}")
        return False


def copiar_build_a_backend():
    """Copia los archivos del build al backend"""
    dist_path = os.path.join(RUTA_FRONTEND, "dist")
    if not os.path.exists(dist_path):
        raise FileNotFoundError("No se encontró la carpeta 'dist'.")
    if not os.path.exists(RUTA_BACKEND):
        os.makedirs(RUTA_BACKEND)
    # limpiar destino
    for elemento in os.listdir(RUTA_BACKEND):
        ruta = os.path.join(RUTA_BACKEND, elemento)
        if os.path.isdir(ruta):
            shutil.rmtree(ruta)
        else:
            os.remove(ruta)
    shutil.copytree(dist_path, RUTA_BACKEND, dirs_exist_ok=True)
    escribir_log("Archivos copiados correctamente al backend.")


# -------------------------------
# INTERFAZ VISUAL (QDialog)
# -------------------------------
class BuildDeployDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 Build & Deploy del Sistema")
        self.setGeometry(550, 320, 500, 380)
        self.setStyleSheet("""
            QLabel, QPushButton, QTextEdit {
                font-family: 'Segoe UI';
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QTextEdit {
                background-color: #f4f4f4;
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 6px;
            }
        """)

        # --- Layouts
        layout = QVBoxLayout()
        self.label_estado = QLabel("Presione el botón para iniciar la actualización.")
        self.label_estado.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label_estado)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        layout.addWidget(self.text_log, stretch=1)

        # --- Botones
        botones_layout = QHBoxLayout()
        self.boton_iniciar = QPushButton("🚀 Iniciar Build + Deploy")
        self.boton_iniciar.clicked.connect(self.iniciar_proceso)
        botones_layout.addWidget(self.boton_iniciar)

        self.boton_cerrar = QPushButton("❌ Cerrar")
        self.boton_cerrar.clicked.connect(self.close)
        botones_layout.addWidget(self.boton_cerrar)
        layout.addLayout(botones_layout)

        self.setLayout(layout)

    # ------------------------------------------------
    # MÉTODOS DEL PROCESO
    # ------------------------------------------------
    def registrar_log(self, mensaje, progreso=None):
        """Actualiza texto visible y barra de progreso"""
        self.text_log.append(f"{mensaje}")
        self.text_log.ensureCursorVisible()
        if progreso is not None:
            self.progress.setValue(progreso)
        self.label_estado.setText(mensaje)
        QApplication.processEvents()
        escribir_log(mensaje)

    def iniciar_proceso(self):
        """Lanza el hilo de ejecución"""
        self.boton_iniciar.setEnabled(False)
        hilo = threading.Thread(target=self.proceso_completo)
        hilo.start()

    def proceso_completo(self):
        """Ejecuta todas las etapas del build + deploy"""
        try:
            self.registrar_log("🔍 Preparando entorno...", 5)
            crear_env_si_no_existe()

            self.registrar_log("🌐 Verificando conexión a internet...", 15)
            conectado = verificar_conexion_internet()
            modo = "REMOTO" if conectado else "LOCAL"
            self.registrar_log(f"Modo detectado: {modo}", 25)

            self.registrar_log("🏗️ Compilando frontend (React)...", 40)
            ok_build = ejecutar_comando("npm run build", cwd=RUTA_FRONTEND)
            if not ok_build:
                raise Exception("Error en la compilación del frontend.")

            self.registrar_log("📦 Copiando archivos al backend...", 70)
            copiar_build_a_backend()

            self.registrar_log("⚙️ Verificando servicio Flask...", 85)
            try:
                r = requests.get("http://localhost:5000", timeout=3)
                if r.status_code == 200:
                    self.registrar_log("✅ Backend en funcionamiento.", 95)
            except Exception:
                self.registrar_log("⚠️ Backend no respondió (posiblemente apagado).", 95)

            self.registrar_log("🎉 Proceso completado exitosamente.", 100)
            QMessageBox.information(self, "Éxito", "El sistema fue actualizado correctamente.")
        except Exception as e:
            self.registrar_log(f"❌ Error: {e}")
            QMessageBox.critical(self, "Error", "No se pudo completar el proceso.\nRevise logs/deploy.log.")
        finally:
            self.boton_iniciar.setEnabled(True)


# -------------------------------
# EJECUCIÓN PRINCIPAL
# -------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialogo = BuildDeployDialog()
    dialogo.show()
    sys.exit(app.exec_())
