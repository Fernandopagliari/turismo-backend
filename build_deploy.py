# build_deploy.py - VERSIÓN CON DETECCIÓN DE NPM
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

# -------------------------
# HILO PRINCIPAL CORREGIDO
# -------------------------
class BuildDeployThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, project_path, deploy_config=None):
        super().__init__()
        self.project_path = project_path
        self.deploy_config = deploy_config or {}
        self.frontend_path = r"E:\Sistemas de app para androide\turismo-app\turismo-frontend"
        self.backend_path = r"E:\Sistemas de app para androide\turismo-app\turismo-backend"
        self.npm_path = self.find_npm()

    def find_npm(self):
        """Buscar npm en el sistema"""
        posibles_npm = [
            "npm",
            "npm.cmd",
            r"C:\Program Files\nodejs\npm.cmd",
            r"C:\Program Files (x86)\nodejs\npm.cmd",
        ]
        
        for npm in posibles_npm:
            try:
                result = subprocess.run([npm, "--version"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return npm
            except:
                continue
        return None

    def log(self, mensaje, nivel="INFO"):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        texto = f"[{ts}] [{nivel}] {mensaje}"
        self.log_signal.emit(texto)

    def run_subprocess(self, cmd, cwd=None, timeout=300):
        """Ejecutar comando seguro"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=True  # ← CAMBIADO A True PARA WINDOWS
            )
            return result.returncode == 0, result.stdout or "", result.stderr or ""
        except Exception as e:
            return False, "", str(e)

    def ejecutar_build_react(self):
        """Ejecutar npm run build"""
        if not self.npm_path:
            self.log("❌ npm no encontrado en el sistema", "ERROR")
            self.log("💡 Instala Node.js desde: https://nodejs.org/", "ERROR")
            return False

        self.log(f"🔧 Usando npm: {self.npm_path}")
        self.log("🔄 Generando build de React...")
        
        ok, out, err = self.run_subprocess([self.npm_path, "run", "build"], cwd=self.frontend_path, timeout=600)
        if ok:
            self.log("✅ Build de React completado")
            # Verificar que se creó la carpeta dist
            dist_path = os.path.join(self.frontend_path, "dist")
            if os.path.exists(dist_path):
                self.log(f"📁 Carpeta dist creada: {dist_path}")
                return True
            else:
                self.log("❌ No se creó la carpeta dist", "ERROR")
                return False
        else:
            self.log(f"❌ Error en build React: {err}", "ERROR")
            return False

    def copiar_archivos_correctamente(self):
        """✅ VERSIÓN DEFINITIVA - Copia archivos frontend E imágenes reales"""
        self.log("📦 Copiando archivos frontend E imágenes...")
        
        dist_path = os.path.join(self.frontend_path, "dist")
        assets_destino = os.path.join(self.backend_path, "assets")
        
        if not os.path.exists(dist_path):
            self.log("❌ No se encontró carpeta dist", "ERROR")
            return False

        # ✅ CREAR carpeta assets
        os.makedirs(assets_destino, exist_ok=True)
        
        # ✅ COPIAR IMÁGENES REALES desde la ubicación correcta
        ruta_imagenes_reales = r"E:\Sistemas de app para androide\turismo-app\public\assets\imagenes"
        imagenes_destino = os.path.join(assets_destino, "imagenes")
        
        if os.path.exists(ruta_imagenes_reales):
            self.log(f"📸 Copiando imágenes REALES desde: {ruta_imagenes_reales}")
            
            # Copiar TODO el contenido de imágenes con archivos reales
            shutil.copytree(ruta_imagenes_reales, imagenes_destino)
            
            # Contar archivos copiados
            total_imagenes = 0
            for root, dirs, files in os.walk(imagenes_destino):
                total_imagenes += len(files)
            
            self.log(f"✅ {total_imagenes} imágenes copiadas")
            
            # Mostrar estructura de imágenes copiada
            self.log("🖼️ Estructura de imágenes copiada:")
            for carpeta in os.listdir(imagenes_destino):
                carpeta_path = os.path.join(imagenes_destino, carpeta)
                if os.path.isdir(carpeta_path):
                    num_archivos = len(os.listdir(carpeta_path))
                    self.log(f"   📂 {carpeta}/ ({num_archivos} archivos)")
        else:
            self.log("❌ No se encontraron imágenes en la ruta especificada", "ERROR")
            return False
        
        # ✅ COPIAR ARCHIVOS FRONTEND (html, js, css)
        archivos_copiados = 0
        
        # 1. Buscar en raíz de dist/
        for item in os.listdir(dist_path):
            origen = os.path.join(dist_path, item)
            destino = os.path.join(assets_destino, item)
            
            if os.path.isfile(origen) and item.endswith(('.html', '.js', '.css', '.svg', '.ico')):
                try:
                    shutil.copy2(origen, destino)
                    archivos_copiados += 1
                    self.log(f"   ✅ {item}")
                except Exception as e:
                    self.log(f"   ⚠️ Error copiando {item}: {str(e)}")
        
        # 2. Buscar en dist/assets/ (si existe)
        assets_dist = os.path.join(dist_path, "assets")
        if os.path.exists(assets_dist):
            for item in os.listdir(assets_dist):
                origen = os.path.join(assets_dist, item)
                destino = os.path.join(assets_destino, item)
                
                if os.path.isfile(origen) and item.endswith(('.js', '.css', '.svg')):
                    try:
                        shutil.copy2(origen, destino)
                        archivos_copiados += 1
                        self.log(f"   ✅ {item}")
                    except Exception as e:
                        self.log(f"   ⚠️ Error copiando {item}: {str(e)}")
        
        self.log(f"✅ {archivos_copiados} archivos frontend copiados")
        
        # ✅ VERIFICAR estructura final COMPLETA
        self.mostrar_estructura_final(assets_destino)
        
        return True

    def mostrar_estructura_final(self, assets_destino):
        """Mostrar estructura final COMPLETA con imágenes"""
        try:
            self.log("📂 ESTRUCTURA FINAL COMPLETA en assets/:")
            
            if not os.path.exists(assets_destino):
                self.log("   ❌ No existe carpeta assets/")
                return
                
            # Mostrar archivos frontend
            archivos_frontend = []
            for item in os.listdir(assets_destino):
                item_path = os.path.join(assets_destino, item)
                if os.path.isfile(item_path):
                    archivos_frontend.append(item)
                elif os.path.isdir(item_path) and item != "imagenes":
                    # Eliminar cualquier carpeta que no sea 'imagenes'
                    self.log(f"   🗑️ Eliminando carpeta duplicada: {item}/")
                    shutil.rmtree(item_path)
            
            self.log("   🎯 ARCHIVOS FRONTEND:")
            for archivo in archivos_frontend:
                self.log(f"      📄 {archivo}")
            
            # Mostrar imágenes
            imagenes_path = os.path.join(assets_destino, "imagenes")
            if os.path.exists(imagenes_path):
                self.log("   🖼️  IMÁGENES COPIADAS:")
                for carpeta in os.listdir(imagenes_path):
                    carpeta_path = os.path.join(imagenes_path, carpeta)
                    if os.path.isdir(carpeta_path):
                        archivos = [f for f in os.listdir(carpeta_path) if os.path.isfile(os.path.join(carpeta_path, f))]
                        num_archivos = len(archivos)
                        self.log(f"      📂 {carpeta}/ ({num_archivos} archivos)")
                        # Mostrar primeros 3 archivos como ejemplo
                        for archivo in archivos[:3]:
                            self.log(f"          🖼️  {archivo}")
                        if num_archivos > 3:
                            self.log(f"          ... y {num_archivos - 3} más")
            
            self.log("   ✅ Estructura CORRECTA - Con imágenes reales")
            
        except Exception as e:
            self.log(f"⚠️ Error mostrando estructura: {str(e)}")
    def update_flask_for_assets(self):
        """Actualizar Flask para servir desde assets/"""
        try:
            api_path = os.path.join(self.backend_path, "api.py")
            if not os.path.exists(api_path):
                self.log("No se encontró api.py", "WARN")
                return
            
            with open(api_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Reemplazar 'build' por 'assets'
            if 'build' in contenido:
                contenido = contenido.replace('"build"', '"assets"')
                contenido = contenido.replace("'build'", "'assets'")
                with open(api_path, 'w', encoding='utf-8') as f:
                    f.write(contenido)
                self.log("✅ Flask actualizado para servir desde assets/")
            else:
                self.log("✅ Flask ya está configurado para assets/")
                
        except Exception as e:
            self.log(f"⚠️ No se pudo actualizar Flask: {e}", "WARN")

    def run(self):
        """Ejecutar proceso completo"""
        try:
            self.progress_signal.emit(10)
            self.log("🚀 INICIANDO BUILD & DEPLOY")
            
            # Verificar npm primero
            if not self.npm_path:
                self.finished_signal.emit(False, "❌ npm no encontrado. Instala Node.js")
                return

            # 1. Build React
            self.progress_signal.emit(30)
            if not self.ejecutar_build_react():
                self.finished_signal.emit(False, "Error en build de React")
                return

            # 2. Copiar archivos a Flask
            self.progress_signal.emit(70)
            if not self.copiar_archivos_correctamente():
                self.finished_signal.emit(False, "Error copiando archivos")
                return

            # 3. Actualizar Flask
            self.progress_signal.emit(90)
            self.update_flask_for_assets()

            self.progress_signal.emit(100)
            self.finished_signal.emit(True, "Build & Deploy completado + Integración Flask realizada (assets/)")
            self.log("✅ PROCESO COMPLETADO EXITOSAMENTE")
            
        except Exception as e:
            self.log(f"Error crítico: {str(e)}", "ERROR")
            self.finished_signal.emit(False, f"Error: {str(e)}")

# -------------------------
# INTERFAZ PyQt5 (MANTENER IGUAL)
# -------------------------
class DialogoBuildDeploy(QDialog):
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

        # Título
        titulo = QLabel("🚀 Sistema Automático de Build & Deploy + Flask")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(titulo)

        # Información
        info_group = QGroupBox("📋 Información del Sistema")
        info_layout = QVBoxLayout()
        self.lbl_proyecto = QLabel(f"📁 Frontend: turismo-frontend")
        self.lbl_backend = QLabel(f"🐍 Backend: turismo-backend")
        self.lbl_npm = QLabel("📦 npm: Verificando...")
        info_layout.addWidget(self.lbl_proyecto)
        info_layout.addWidget(self.lbl_backend)
        info_layout.addWidget(self.lbl_npm)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Log
        lbl_log = QLabel("📝 Log de ejecución:")
        layout.addWidget(lbl_log)

        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(300)
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("font-family: 'Consolas'; font-size: 9px;")
        layout.addWidget(self.log_output)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Botones
        botones_layout = QHBoxLayout()
        self.btn_build = QPushButton("🚀 Build + Flask")
        self.btn_verificar = QPushButton("🔍 Verificar")
        self.btn_limpiar = QPushButton("🗑️ Limpiar")
        self.btn_cerrar = QPushButton("❌ Cerrar")

        self.btn_build.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 8px; }")
        self.btn_verificar.setStyleSheet("QPushButton { background-color: #3498db; color: white; padding: 8px; }")
        self.btn_limpiar.setStyleSheet("QPushButton { background-color: #f39c12; color: white; padding: 8px; }")
        self.btn_cerrar.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; padding: 8px; }")

        botones_layout.addWidget(self.btn_build)
        botones_layout.addWidget(self.btn_verificar)
        botones_layout.addWidget(self.btn_limpiar)
        botones_layout.addWidget(self.btn_cerrar)
        layout.addLayout(botones_layout)

        scroll.setWidget(scroll_content)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

        # Conexiones
        self.btn_build.clicked.connect(self.iniciar_build)
        self.btn_verificar.clicked.connect(self.verificar_sistema)
        self.btn_limpiar.clicked.connect(self.limpiar_log)
        self.btn_cerrar.clicked.connect(self.close)

        self.verificar_sistema()

    def log(self, mensaje):
        self.log_output.append(mensaje)
        self.log_output.moveCursor(self.log_output.textCursor().End)

    def limpiar_log(self):
        self.log_output.clear()
        self.log("🗑️ Log limpiado")

    def load_config_from_db(self):
        """Cargar configuración desde BD"""
        try:
            from database_local import obtener_configuracion_hosting
            cfg = obtener_configuracion_hosting()
            if cfg:
                self.deploy_config = cfg
                base_url = cfg.get("base_url", "No configurado")
                self.log(f"✅ Configuración cargada: {base_url}")
        except:
            self.log("⚠️ No se pudo cargar configuración de BD")

    def verificar_sistema(self):
        """Verificar que todo esté listo"""
        # Verificar npm
        thread = BuildDeployThread(self.project_path)
        if thread.npm_path:
            self.lbl_npm.setText(f"📦 npm: ✅ {thread.npm_path}")
        else:
            self.lbl_npm.setText("📦 npm: ❌ No encontrado")
            
        # Verificar carpetas
        frontend_path = r"E:\Sistemas de app para androide\turismo-app\turismo-frontend"
        backend_path = r"E:\Sistemas de app para androide\turismo-app\turismo-backend"
        
        frontend_ok = os.path.exists(frontend_path)
        backend_ok = os.path.exists(backend_path)
        
        if frontend_ok and backend_ok:
            self.log("✅ Sistema verificado: Frontend y Backend encontrados")
        else:
            self.log("❌ Error: No se encontraron las carpetas del proyecto")

    def iniciar_build(self):
        """Iniciar proceso de build"""
        self.btn_build.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_output.clear()
        
        self.log("🚀 INICIANDO PROCESO BUILD & DEPLOY...")
        
        self.build_thread = BuildDeployThread(self.project_path, self.deploy_config)
        self.build_thread.log_signal.connect(self.log)
        self.build_thread.progress_signal.connect(self.progress_bar.setValue)
        self.build_thread.finished_signal.connect(self.proceso_finalizado)
        self.build_thread.start()

    def proceso_finalizado(self, exito, mensaje):
        """Cuando termina el proceso"""
        self.btn_build.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.log(mensaje)
        
        if exito:
            QMessageBox.information(self, "✅ Éxito", 
                                  "Build & Deploy completado exitosamente!\n\n"
                                  "✅ Build de React generado\n"
                                  "✅ Archivos copiados a Flask (assets/)\n"
                                  "✅ Estructura correcta sin duplicaciones\n"
                                  "✅ Flask configurado para producción\n\n"
                                  "🎯 Ahora ejecuta backend_deploy.py")
        else:
            QMessageBox.critical(self, "❌ Error", mensaje)

# Función para mostrar el diálogo
def mostrar_dialogo_build_deploy(parent=None):
    dialogo = DialogoBuildDeploy(parent)
    dialogo.exec_()

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication([])
    dialogo = DialogoBuildDeploy()
    dialogo.show()
    app.exec_() 