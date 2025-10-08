# build_deploy.py - CON INTEGRACIÓN FLASK REACT
import os
import subprocess
import sys
import shutil
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QProgressBar, QMessageBox,
                             QGroupBox, QComboBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import threading

# Importar la conexión a la base de datos
try:
    from database_local import conectar_local, obtener_configuracion_hosting
    BD_DISPONIBLE = True
except ImportError:
    BD_DISPONIBLE = False

class BuildDeployThread(QThread):
    """Hilo para ejecutar build y deploy sin bloquear la UI - CON FLASK INTEGRADO"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, project_path, deploy_config=None):
        super().__init__()
        self.project_path = project_path
        self.deploy_config = deploy_config or {}
        
        # Rutas posibles del proyecto
        self.possible_paths = [
            project_path,  # Raíz del proyecto
            os.path.join(project_path, "src"),
            os.path.join(project_path, "frontend"),
        ]
        
        self.project_root = self.encontrar_project_root()
        self.dist_path = os.path.join(self.project_root, "dist") if self.project_root else None
        
        # ✅ Ruta del backend Flask para integración
        self.backend_path = self.encontrar_backend_path()
        self.react_build_dest = os.path.join(self.backend_path, "react-build") if self.backend_path else None
        
        # ✅ Encontrar npm y node
        self.npm_path = self.encontrar_npm()
        self.node_path = self.encontrar_node()
        
    def encontrar_backend_path(self):
        """Encontrar la ruta del backend Flask"""
        # Buscar en diferentes ubicaciones posibles
        posibles_backends = [
            r"E:\Sistemas de app para androide\turismo-backend",
            os.path.join(os.path.dirname(self.project_path), "turismo-backend"),
            os.path.join(os.path.dirname(os.path.dirname(self.project_path)), "turismo-backend"),
            os.path.join(os.path.expanduser("~"), "turismo-backend"),
        ]
        
        for backend_path in posibles_backends:
            if os.path.exists(backend_path):
                # Verificar que tiene api.py (backend Flask)
                api_py = os.path.join(backend_path, "api.py")
                if os.path.exists(api_py):
                    print(f"✅ Backend Flask encontrado en: {backend_path}")
                    return backend_path
                else:
                    print(f"⚠️  Carpeta encontrada pero sin api.py: {backend_path}")
        
        print("❌ Backend Flask no encontrado")
        return None
    
    def encontrar_npm(self):
        """Encontrar la ruta de npm"""
        # Buscar npm en diferentes ubicaciones
        posibles_rutas = [
            "npm",  # En PATH
            r"C:\Program Files\nodejs\npm.cmd",
            r"C:\Program Files (x86)\nodejs\npm.cmd",
            os.path.join(os.environ.get('APPDATA', ''), "npm", "npm.cmd"),
        ]
        
        for ruta in posibles_rutas:
            try:
                result = subprocess.run([ruta, "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ npm encontrado en: {ruta}")
                    return ruta
            except:
                continue
        
        print("❌ npm no encontrado")
        return None
    
    def encontrar_node(self):
        """Encontrar la ruta de node"""
        # Buscar node en diferentes ubicaciones
        posibles_rutas = [
            "node",  # En PATH
            r"C:\Program Files\nodejs\node.exe",
            r"C:\Program Files (x86)\nodejs\node.exe",
        ]
        
        for ruta in posibles_rutas:
            try:
                result = subprocess.run([ruta, "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ node encontrado en: {ruta}")
                    return ruta
            except:
                continue
        
        print("❌ node no encontrado")
        return None
        
    def encontrar_project_root(self):
        """Encontrar la raíz del proyecto React (donde está package.json)"""
        for path in self.possible_paths:
            if os.path.exists(path):
                package_json = os.path.join(path, "package.json")
                if os.path.exists(package_json):
                    print(f"✅ Encontrado package.json en: {path}")
                    return path
                else:
                    print(f"❌ package.json no encontrado en: {path}")
        
        return None
        
    def run(self):
        try:
            self.log_signal.emit("🚀 INICIANDO PROCESO DE BUILD & DEPLOY CON FLASK")
            self.log_signal.emit("=" * 50)
            
            # Paso 1: Verificar que encontramos el proyecto
            if not self.project_root:
                error_msg = f"❌ No se pudo encontrar el proyecto React.\n"
                error_msg += f"Buscado en:\n"
                for path in self.possible_paths:
                    error_msg += f"  - {path}\n"
                error_msg += f"💡 Asegúrate de que package.json existe en una de estas rutas"
                self.finished_signal.emit(False, error_msg)
                return
                
            self.log_signal.emit(f"✅ Proyecto encontrado en: {self.project_root}")
            
            # Paso 2: Verificar npm y node
            if not self.npm_path or not self.node_path:
                error_msg = "❌ Node.js o npm no encontrados.\n"
                error_msg += "💡 Instala Node.js desde: https://nodejs.org/\n"
                error_msg += "💡 O asegúrate de que están en el PATH del sistema"
                self.finished_signal.emit(False, error_msg)
                return
                
            self.log_signal.emit(f"✅ Node.js encontrado: {self.node_path}")
            self.log_signal.emit(f"✅ npm encontrado: {self.npm_path}")
            
            # Paso 3: Verificar backend Flask
            if self.backend_path:
                self.log_signal.emit(f"✅ Backend Flask encontrado: {self.backend_path}")
            else:
                self.log_signal.emit("⚠️  Backend Flask no encontrado - Solo generando build")
                
            # Paso 4: Navegar al directorio del proyecto
            os.chdir(self.project_root)
            self.log_signal.emit(f"📁 Directorio de trabajo: {self.project_root}")
            
            # Paso 5: Mostrar configuración de deploy
            if self.deploy_config:
                self.log_signal.emit(f"🌐 Configuración de deploy: {self.deploy_config.get('base_url', 'No configurado')}")
            
            # Paso 6: Instalar dependencias si es necesario
            self.log_signal.emit("📦 Verificando dependencias...")
            self.progress_signal.emit(10)
            
            if not self.verificar_dependencias():
                self.log_signal.emit("⚠️ Instalando dependencias...")
                if not self.instalar_dependencias():
                    self.finished_signal.emit(False, "Error instalando dependencias")
                    return
            
            self.progress_signal.emit(30)
            
            # Paso 7: Ejecutar build
            self.log_signal.emit("🔨 Ejecutando build...")
            if not self.ejecutar_build():
                self.finished_signal.emit(False, "Error en el build")
                return
                
            self.progress_signal.emit(70)
            
            # ✅ PASO NUEVO: Copiar build a Flask
            if self.backend_path and self.dist_path and os.path.exists(self.dist_path):
                self.log_signal.emit("📦 Integrando con Flask...")
                if self.copiar_build_a_flask():
                    self.log_signal.emit("🎯 Frontend React integrado con backend Flask")
                    self.progress_signal.emit(80)
                else:
                    self.log_signal.emit("⚠️  Build generado pero no integrado con Flask")
                    self.progress_signal.emit(75)
            else:
                self.log_signal.emit("ℹ️  Build generado (sin integración Flask)")
                self.progress_signal.emit(75)
            
            # Paso 8: Deploy (solo si hay configuración)
            if self.deploy_config and self.deploy_config.get('base_url'):
                self.log_signal.emit("☁️ Realizando deploy...")
                if not self.ejecutar_deploy():
                    self.finished_signal.emit(False, "Error en el deploy")
                    return
            else:
                self.log_signal.emit("ℹ️  Solo build - No hay configuración de deploy")
                
            self.progress_signal.emit(100)
            
            # Mensaje final según integración
            if self.backend_path and os.path.exists(self.react_build_dest):
                mensaje_final = "✅ Build & Deploy completado + Flask integrado!"
            else:
                mensaje_final = "✅ Build & Deploy completado!"
                
            self.finished_signal.emit(True, mensaje_final)
            
        except Exception as e:
            self.finished_signal.emit(False, f"❌ Error: {str(e)}")
    
    def copiar_build_a_flask(self):
        """Copiar el build de React a la carpeta del backend Flask"""
        try:
            self.log_signal.emit(f"📦 Copiando build a Flask...")
            self.log_signal.emit(f"📍 Origen: {self.dist_path}")
            self.log_signal.emit(f"📍 Destino: {self.react_build_dest}")
            
            # Verificar que existe el build
            if not os.path.exists(self.dist_path):
                self.log_signal.emit("❌ No se encontró la carpeta dist del build")
                return False
            
            # Limpiar destino anterior
            if os.path.exists(self.react_build_dest):
                shutil.rmtree(self.react_build_dest)
                self.log_signal.emit("🗑️ Build anterior eliminado")
            
            # Copiar nuevo build
            shutil.copytree(self.dist_path, self.react_build_dest)
            self.log_signal.emit(f"✅ Build copiado a Flask")
            
            # Mostrar información del build copiado
            if os.path.exists(self.react_build_dest):
                tamaño = self.get_folder_size(self.react_build_dest)
                self.log_signal.emit(f"📊 Tamaño del build en Flask: {tamaño}")
                
                # Verificar archivos críticos
                archivos_criticos = ['index.html', 'assets/', 'static/']
                archivos_existentes = os.listdir(self.react_build_dest)
                
                for critico in archivos_criticos:
                    if critico.replace('/', '') in archivos_existentes:
                        self.log_signal.emit(f"✅ {critico} encontrado")
                    else:
                        self.log_signal.emit(f"⚠️  {critico} no encontrado")
            
            return True
            
        except Exception as e:
            self.log_signal.emit(f"❌ Error copiando build a Flask: {str(e)}")
            return False
    
    def verificar_dependencias(self):
        """Verificar si node_modules existe"""
        node_modules_path = os.path.join(self.project_root, "node_modules")
        existe = os.path.exists(node_modules_path)
        self.log_signal.emit(f"📦 node_modules existe: {existe}")
        return existe
    
    def instalar_dependencias(self):
        """Ejecutar npm install"""
        try:
            self.log_signal.emit("📥 Instalando dependencias con npm install...")
            
            # Usar la ruta completa de npm
            comando = [self.npm_path, "install"]
            
            result = subprocess.run(comando, 
                                  capture_output=True, text=True, 
                                  timeout=300,  # 5 minutos
                                  shell=True)  # ✅ Usar shell para acceso a PATH
            
            if result.returncode == 0:
                self.log_signal.emit("✅ Dependencias instaladas correctamente")
                if result.stdout:
                    self.log_signal.emit(f"📋 Output: {result.stdout[-200:]}")  # Últimas 200 chars
                return True
            else:
                self.log_signal.emit(f"❌ Error instalando dependencias")
                if result.stderr:
                    self.log_signal.emit(f"🔴 Stderr: {result.stderr}")
                if result.stdout:
                    self.log_signal.emit(f"🟡 Stdout: {result.stdout}")
                return False
                
        except subprocess.TimeoutExpired:
            self.log_signal.emit("❌ Timeout instalando dependencias")
            return False
        except Exception as e:
            self.log_signal.emit(f"❌ Error: {str(e)}")
            return False
    
    def ejecutar_build(self):
        """Ejecutar npm run build"""
        try:
            self.log_signal.emit("🏗️ Ejecutando npm run build...")
            
            # Limpiar dist anterior si existe
            if os.path.exists(self.dist_path):
                shutil.rmtree(self.dist_path)
                self.log_signal.emit("🗑️ Carpeta dist anterior eliminada")
            
            # Usar la ruta completa de npm
            comando = [self.npm_path, "run", "build"]
            
            result = subprocess.run(comando, 
                                  capture_output=True, text=True, 
                                  timeout=300,  # 5 minutos
                                  shell=True)  # ✅ Usar shell para acceso a PATH
            
            if result.returncode == 0:
                self.log_signal.emit("✅ Build completado exitosamente")
                self.log_signal.emit(f"📂 Carpeta dist creada en: {self.dist_path}")
                
                # Mostrar información del build
                if os.path.exists(self.dist_path):
                    tamaño = self.get_folder_size(self.dist_path)
                    self.log_signal.emit(f"📊 Tamaño del build: {tamaño}")
                    
                    # Mostrar archivos generados
                    archivos = self.listar_archivos_dist()
                    self.log_signal.emit(f"📄 Archivos generados: {', '.join(archivos)}")
                    
                return True
            else:
                self.log_signal.emit(f"❌ Error en build")
                if result.stderr:
                    self.log_signal.emit(f"🔴 Stderr: {result.stderr}")
                if result.stdout:
                    self.log_signal.emit(f"🟡 Stdout: {result.stdout}")
                return False
                
        except subprocess.TimeoutExpired:
            self.log_signal.emit("❌ Timeout en build")
            return False
        except Exception as e:
            self.log_signal.emit(f"❌ Error: {str(e)}")
            return False
    
    def ejecutar_deploy(self):
        """Ejecutar deploy basado en la configuración de la BD"""
        try:
            base_url = self.deploy_config.get('base_url', '')
            
            if not base_url:
                self.log_signal.emit("⚠️  No hay base_url configurado para deploy")
                return True
            
            # Determinar el tipo de deploy basado en el base_url
            if 'railway' in base_url:
                return self.deploy_railway()
            elif 'netlify' in base_url:
                return self.deploy_netlify()
            elif 'vercel' in base_url:
                return self.deploy_vercel()
            else:
                # Deploy genérico (FTP, SSH, etc.)
                return self.deploy_generico()
                
        except Exception as e:
            self.log_signal.emit(f"❌ Error en deploy: {str(e)}")
            return False
    
    def deploy_railway(self):
        """Deploy automático a Railway"""
        try:
            self.log_signal.emit("🚂 Desplegando a Railway...")
            
            # Verificar que railway CLI está instalado
            result = subprocess.run(["railway", "--version"], 
                                  capture_output=True, text=True,
                                  shell=True)  # ✅ Usar shell
            
            if result.returncode != 0:
                self.log_signal.emit("❌ Railway CLI no encontrado. Instala con: npm install -g @railway/cli")
                self.log_signal.emit("💡 Deploy manual requerido")
                return True  # No es error crítico, solo build
            
            # Deploy con railway
            result = subprocess.run(["railway", "deploy"], 
                                  capture_output=True, text=True, 
                                  timeout=600,
                                  shell=True)  # ✅ Usar shell
            
            if result.returncode == 0:
                self.log_signal.emit("✅ Deploy a Railway completado")
                self.log_signal.emit(f"🌐 Aplicación disponible en: {self.deploy_config.get('base_url')}")
                return True
            else:
                self.log_signal.emit(f"❌ Error en deploy Railway: {result.stderr}")
                self.log_signal.emit("💡 Deploy manual requerido")
                return True  # No es error crítico, solo build
                
        except subprocess.TimeoutExpired:
            self.log_signal.emit("❌ Timeout en deploy Railway")
            return True
        except Exception as e:
            self.log_signal.emit(f"❌ Error: {str(e)}")
            return True
    
    def deploy_netlify(self):
        """Deploy a Netlify"""
        self.log_signal.emit("☁️  Configuración Netlify detectada")
        self.log_signal.emit("💡 Deploy manual requerido para Netlify")
        self.log_signal.emit(f"🔗 Sube la carpeta 'dist' a: {self.deploy_config.get('base_url')}")
        return True
    
    def deploy_vercel(self):
        """Deploy a Vercel"""
        self.log_signal.emit("▲ Configuración Vercel detectada")
        self.log_signal.emit("💡 Deploy manual requerido para Vercel")
        self.log_signal.emit(f"🔗 Sube la carpeta 'dist' a: {self.deploy_config.get('base_url')}")
        return True
    
    def deploy_generico(self):
        """Deploy genérico"""
        self.log_signal.emit("🌐 Configuración de deploy genérico")
        self.log_signal.emit(f"🔗 URL de producción: {self.deploy_config.get('base_url')}")
        self.log_signal.emit("💡 Sube manualmente la carpeta 'dist' a tu servidor")
        return True
    
    def get_folder_size(self, folder_path):
        """Calcular tamaño de carpeta en MB"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    total_size += os.path.getsize(filepath)
            
            size_mb = total_size / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        except:
            return "Desconocido"
    
    def listar_archivos_dist(self):
        """Listar archivos principales en dist"""
        try:
            if not os.path.exists(self.dist_path):
                return ["No existe dist"]
            
            archivos = []
            for item in os.listdir(self.dist_path):
                if os.path.isfile(os.path.join(self.dist_path, item)):
                    archivos.append(item)
                elif os.path.isdir(os.path.join(self.dist_path, item)):
                    archivos.append(f"{item}/")
            
            return archivos[:5]  # Solo primeros 5 archivos
        except:
            return ["Error listando archivos"]

class DialogoBuildDeploy(QDialog):
    """Diálogo para build y deploy automático - CON FLASK INTEGRADO"""
    
    def __init__(self, parent=None, project_path=None):
        super().__init__(parent)
        # ✅ CORREGIDO: Apuntar a la raíz del proyecto (donde está package.json)
        self.project_path = project_path or r"E:\Sistemas de app para androide\turismo-app"
        self.deploy_config = None
        self.setup_ui()
        self.cargar_configuracion_desde_bd()
        
    def setup_ui(self):
        self.setWindowTitle("🚀 Build & Deploy Automático + Flask")
        self.setFixedSize(700, 600)
        
        layout = QVBoxLayout()
        
        # Título
        titulo = QLabel("Sistema Automático de Build & Deploy + Flask")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin: 10px;")
        layout.addWidget(titulo)
        
        # Información del proyecto
        info_group = QGroupBox("📋 Información del Proyecto")
        info_layout = QVBoxLayout()
        
        self.lbl_proyecto = QLabel(f"📁 Proyecto: {self.project_path}")
        self.lbl_deploy = QLabel("🌐 Deploy: Cargando configuración...")
        self.lbl_url = QLabel("🔗 URL: Cargando...")
        self.lbl_flask = QLabel("🐍 Flask: Verificando...")
        
        info_layout.addWidget(self.lbl_proyecto)
        info_layout.addWidget(self.lbl_deploy)
        info_layout.addWidget(self.lbl_url)
        info_layout.addWidget(self.lbl_flask)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Log output
        layout.addWidget(QLabel("📝 Log de ejecución:"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("font-family: 'Courier New'; font-size: 10px;")
        layout.addWidget(self.log_output)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Botones
        botones_layout = QHBoxLayout()
        
        self.btn_build_only = QPushButton("🔨 Solo Build")
        self.btn_build_only.clicked.connect(lambda: self.iniciar_proceso(None))
        self.btn_build_only.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        
        self.btn_build_deploy = QPushButton("🚀 Build + Deploy")
        self.btn_build_deploy.clicked.connect(lambda: self.iniciar_proceso(self.deploy_config))
        self.btn_build_deploy.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #219a52; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        
        self.btn_cerrar = QPushButton("❌ Cerrar")
        self.btn_cerrar.clicked.connect(self.close)
        self.btn_cerrar.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        
        botones_layout.addWidget(self.btn_build_only)
        botones_layout.addWidget(self.btn_build_deploy)
        botones_layout.addWidget(self.btn_cerrar)
        layout.addLayout(botones_layout)
        
        self.setLayout(layout)
        
        # Thread
        self.build_thread = None
        
        # Verificar Flask inicialmente
        self.verificar_flask_inicial()
    
    def verificar_flask_inicial(self):
        """Verificar estado de Flask al iniciar"""
        try:
            # Simular la búsqueda de Flask como lo hace el thread
            posibles_backends = [
                r"E:\Sistemas de app para androide\turismo-backend",
                os.path.join(os.path.dirname(self.project_path), "turismo-backend"),
            ]
            
            for backend_path in posibles_backends:
                if os.path.exists(backend_path) and os.path.exists(os.path.join(backend_path, "api.py")):
                    self.lbl_flask.setText(f"🐍 Flask: ✅ CONECTADO - {os.path.basename(backend_path)}")
                    return
            
            self.lbl_flask.setText("🐍 Flask: ❌ NO ENCONTRADO")
            
        except Exception as e:
            self.lbl_flask.setText(f"🐍 Flask: ⚠️ ERROR - {str(e)}")
    
    def cargar_configuracion_desde_bd(self):
        """Cargar configuración de deploy desde la base de datos"""
        try:
            if not BD_DISPONIBLE:
                self.actualizar_ui_configuracion(None, "Base de datos no disponible")
                return
            
            config = obtener_configuracion_hosting()
            if config:
                self.deploy_config = config
                base_url = config.get('base_url', 'No configurado')
                host = config.get('host', 'Desconocido')
                
                self.actualizar_ui_configuracion(base_url, host)
                self.log(f"✅ Configuración cargada desde BD: {base_url}")
            else:
                self.actualizar_ui_configuracion(None, "No hay configuración de hosting")
                self.log("⚠️  No se encontró configuración de deploy en la BD")
                
        except Exception as e:
            self.actualizar_ui_configuracion(None, f"Error: {str(e)}")
            self.log(f"❌ Error cargando configuración: {str(e)}")
    
    def actualizar_ui_configuracion(self, base_url, host_info):
        """Actualizar la UI con la configuración cargada"""
        if base_url:
            self.lbl_deploy.setText(f"🌐 Deploy: {host_info}")
            self.lbl_url.setText(f"🔗 URL: {base_url}")
            self.btn_build_deploy.setEnabled(True)
        else:
            self.lbl_deploy.setText("🌐 Deploy: No configurado")
            self.lbl_url.setText("🔗 URL: No configurado")
            self.btn_build_deploy.setEnabled(False)
    
    def log(self, mensaje):
        """Agregar mensaje al log"""
        self.log_output.append(f"{mensaje}")
        # Auto-scroll
        cursor = self.log_output.textCursor()
        cursor.movePosition(cursor.End)
        self.log_output.setTextCursor(cursor)
    
    def iniciar_proceso(self, deploy_config):
        """Iniciar proceso de build/deploy"""
        # Deshabilitar botones
        self.btn_build_only.setEnabled(False)
        self.btn_build_deploy.setEnabled(False)
        
        # Mostrar progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Limpiar log anterior
        self.log_output.clear()
        
        # Crear y ejecutar thread
        self.build_thread = BuildDeployThread(self.project_path, deploy_config)
        self.build_thread.log_signal.connect(self.log)
        self.build_thread.progress_signal.connect(self.progress_bar.setValue)
        self.build_thread.finished_signal.connect(self.proceso_finalizado)
        self.build_thread.start()
    
    def proceso_finalizado(self, exito, mensaje):
        """Callback cuando termina el proceso"""
        # Habilitar botones
        self.btn_build_only.setEnabled(True)
        self.btn_build_deploy.setEnabled(True)
        
        # Ocultar progress bar
        self.progress_bar.setVisible(False)
        
        # Mostrar mensaje final
        self.log(mensaje)
        
        # Actualizar estado de Flask
        self.verificar_flask_inicial()
        
        if exito:
            QMessageBox.information(self, "✅ Éxito", mensaje)
        else:
            QMessageBox.critical(self, "❌ Error", mensaje)

def mostrar_dialogo_build_deploy(parent=None):
    """Función para mostrar el diálogo de build & deploy"""
    dialogo = DialogoBuildDeploy(parent)
    dialogo.exec_()

# Para probar directamente
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication([])
    dialogo = DialogoBuildDeploy()
    dialogo.show()
    app.exec_()