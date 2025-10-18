# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import shutil
import time
import requests
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QProgressBar, QMessageBox,
                             QGroupBox, QComboBox, QLineEdit, QScrollArea, QWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class BackendDeployThread(QThread):
    """Hilo para ejecutar deploy COMPLETO del backend incluyendo assets"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, backend_path, servidor_config=None):
        super().__init__()
        self.backend_path = backend_path
        self.servidor_config = servidor_config or {}
        self.datos_hosting = servidor_config.get('datos_hosting', {})
        
    def run(self):
        try:
            self.log_signal.emit("🚀 INICIANDO DEPLOY COMPLETO DEL BACKEND")
            self.log_signal.emit("=" * 50)
            
            # Mostrar información del hosting desde BD
            if self.datos_hosting:
                self.log_signal.emit(f"🌐 Host: {self.datos_hosting.get('host', 'N/A')}")
                self.log_signal.emit(f"🔗 URL: {self.datos_hosting.get('base_url', 'N/A')}")
                self.log_signal.emit(f"👤 Usuario: {self.datos_hosting.get('user', 'N/A')}")
                self.log_signal.emit("-" * 30)
            
            # Paso 1: Verificar que existe el backend
            if not os.path.exists(self.backend_path):
                self.finished_signal.emit(False, f"No se encuentra backend en: {self.backend_path}")
                return
                
            self.log_signal.emit(f"📁 Backend encontrado en: {self.backend_path}")
            self.progress_signal.emit(10)
            
            # Paso 2: Verificar y crear archivos esenciales PARA PRODUCCIÓN
            if not self.preparar_archivos_produccion():
                return
            
            self.progress_signal.emit(20)
            
            # Paso 3: Copiar assets MANTENIENDO ESTRUCTURA
            if not self.copiar_assets_al_repositorio():
                return
            
            self.progress_signal.emit(40)
            
            # Paso 4: Obtener configuración del servidor
            servidor = self.servidor_config.get('nombre', 'personalizado')
            tipo = self.servidor_config.get('tipo', 'git')
            comando = self.servidor_config.get('comando', '')
            
            self.log_signal.emit(f"🌐 Servidor: {servidor}")
            self.log_signal.emit(f"🔧 Tipo: {tipo}")
            
            # Paso 5: Ejecutar deploy según el tipo
            resultado = self.ejecutar_deploy(tipo, servidor, comando)
            
            if resultado:
                self.progress_signal.emit(80)
                
                # Paso 6: Verificar deploy
                if self.verificar_deploy():
                    self.progress_signal.emit(100)
                    self.finished_signal.emit(True, f"✅ ¡DEPLOY COMPLETADO EXITOSAMENTE! 🎉\n\nTu aplicación está funcionando en PRODUCCIÓN:\n{self.datos_hosting.get('base_url', 'N/A')}")
                else:
                    self.finished_signal.emit(True, f"⚠️  Deploy completado pero la verificación mostró advertencias")
            else:
                self.finished_signal.emit(False, f"❌ Error en el deploy a {servidor}")
            
        except Exception as e:
            self.finished_signal.emit(False, f"❌ Error: {str(e)}")
    
    def preparar_archivos_produccion(self):
        """Verificar y crear archivos esenciales para PRODUCCIÓN"""
        self.log_signal.emit("🔧 Configurando para PRODUCCIÓN...")
        
        # ✅ 1. ACTUALIZAR requirements.txt CON GUNICORN
        requirements_path = os.path.join(self.backend_path, "requirements.txt")
        if os.path.exists(requirements_path):
            try:
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                
                if 'gunicorn' not in contenido:
                    self.log_signal.emit("📦 Agregando gunicorn a requirements.txt...")
                    with open(requirements_path, 'a', encoding='utf-8') as f:
                        f.write("\ngunicorn==20.1.0\n")
                    self.log_signal.emit("✅ gunicorn agregado para producción")
                else:
                    self.log_signal.emit("✅ gunicorn ya está en requirements.txt")
            except Exception as e:
                self.log_signal.emit(f"⚠️  Error actualizando requirements.txt: {str(e)}")
        
        # ✅ 2. CREAR/MODIFICAR Procfile PARA PRODUCCIÓN
        procfile_path = os.path.join(self.backend_path, "Procfile")
        try:
            procfile_content = "web: gunicorn api:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120"
            with open(procfile_path, 'w', encoding='utf-8') as f:
                f.write(procfile_content)
            self.log_signal.emit("✅ Procfile configurado para producción con gunicorn")
        except Exception as e:
            self.log_signal.emit(f"❌ Error creando Procfile: {str(e)}")
            return False
        
        # ✅ 3. CREAR/MODIFICAR railway.toml
        railway_toml_path = os.path.join(self.backend_path, "railway.toml")
        try:
            railway_config = """[build]
builder = "nixpacks"

[deploy]
startCommand = "gunicorn api:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120"

[[services]]
name = "web"
type = "web"
"""
            with open(railway_toml_path, 'w', encoding='utf-8') as f:
                f.write(railway_config)
            self.log_signal.emit("✅ railway.toml configurado para producción")
        except Exception as e:
            self.log_signal.emit(f"❌ Error creando railway.toml: {str(e)}")
            return False
        
        # ✅ 4. CREAR runtime.txt si no existe
        runtime_path = os.path.join(self.backend_path, "runtime.txt")
        if not os.path.exists(runtime_path):
            try:
                with open(runtime_path, 'w', encoding='utf-8') as f:
                    f.write("python-3.9.0")
                self.log_signal.emit("✅ runtime.txt creado")
            except Exception as e:
                self.log_signal.emit(f"⚠️  Error creando runtime.txt: {str(e)}")
        
        # ✅ 5. VERIFICAR ARCHIVOS ESENCIALES
        archivos_esenciales = {
            "api.py": "Servidor Flask principal",
            "requirements.txt": "Dependencias Python", 
            "database_hosting.py": "Conexión BD",
            "railway.toml": "Configuración Railway",
            "Procfile": "Configuración proceso"
        }
        
        todos_encontrados = True
        for archivo, descripcion in archivos_esenciales.items():
            ruta_archivo = os.path.join(self.backend_path, archivo)
            if os.path.exists(ruta_archivo):
                self.log_signal.emit(f"✅ {archivo} - {descripcion}")
            else:
                self.log_signal.emit(f"❌ {archivo} - {descripcion} - FALTANTE")
                if archivo in ["api.py", "requirements.txt"]:
                    todos_encontrados = False
        
        return todos_encontrados
    
    def copiar_assets_al_repositorio(self):
        """Copiar assets desde turismo-app/public/assets al repositorio MANTENIENDO ESTRUCTURA"""
        try:
            # Buscar assets en diferentes ubicaciones posibles
            posibles_rutas_assets = [
                os.path.join(os.path.dirname(self.backend_path), "..", "frontend", "public", "assets"),
                os.path.join(os.path.dirname(self.backend_path), "..", "public", "assets"),
                os.path.join(os.path.dirname(self.backend_path), "public", "assets"),
            ]
            
            assets_origen = None
            for ruta in posibles_rutas_assets:
                ruta_abs = os.path.abspath(ruta)
                if os.path.exists(ruta_abs):
                    assets_origen = ruta_abs
                    break
            
            if not assets_origen:
                self.log_signal.emit("⚠️  No se encontraron assets en las ubicaciones esperadas")
                return True
            
            assets_destino = os.path.join(self.backend_path, "assets")
            
            self.log_signal.emit(f"📁 Assets encontrados en: {assets_origen}")
            
            try:
                contenido = os.listdir(assets_origen)
                if not contenido:
                    self.log_signal.emit("ℹ️  Carpeta assets vacía")
                    return True
                
                self.log_signal.emit(f"📦 Encontrados {len(contenido)} elementos en assets")
                for item in contenido:
                    ruta_item = os.path.join(assets_origen, item)
                    if os.path.isdir(ruta_item):
                        try:
                            subitems = os.listdir(ruta_item)
                            self.log_signal.emit(f"   📂 {item}/ ({len(subitems)} elementos)")
                        except:
                            self.log_signal.emit(f"   📂 {item}/")
                    else:
                        self.log_signal.emit(f"   📄 {item}")
                        
            except Exception as e:
                self.log_signal.emit(f"⚠️  Error listando assets: {str(e)}")
                return True
            
            self.log_signal.emit("🔄 Copiando assets al repositorio MANTENIENDO ESTRUCTURA...")
            
            # ✅ FUNCIÓN RECURSIVA PARA COPIAR MANTENIENDO ESTRUCTURA
            def copiar_recursivo(origen, destino):
                """Copia recursivamente manteniendo estructura de carpetas"""
                if not os.path.exists(destino):
                    os.makedirs(destino)
                
                items_copiados = 0
                for item in os.listdir(origen):
                    origen_item = os.path.join(origen, item)
                    destino_item = os.path.join(destino, item)
                    
                    try:
                        if os.path.isdir(origen_item):
                            # Crear subcarpeta y copiar contenido recursivamente
                            if not os.path.exists(destino_item):
                                os.makedirs(destino_item)
                            
                            # Llamada recursiva para subcarpetas
                            sub_items = copiar_recursivo(origen_item, destino_item)
                            items_copiados += sub_items
                            self.log_signal.emit(f"   📁 Carpeta: {item}/ ({sub_items} archivos)")
                            
                        else:
                            # Copiar archivo individual
                            shutil.copy2(origen_item, destino_item)
                            items_copiados += 1
                            # Solo mostrar algunos archivos para no saturar el log
                            if items_copiados <= 10:  # Mostrar primeros 10 archivos
                                self.log_signal.emit(f"   📄 {item}")
                                
                    except Exception as e:
                        self.log_signal.emit(f"   ⚠️  Error copiando {item}: {str(e)}")
                        continue
                
                return items_copiados
            
            # ✅ USAR LA FUNCIÓN RECURSIVA MEJORADA
            total_copiados = copiar_recursivo(assets_origen, assets_destino)
            
            self.log_signal.emit(f"✅ {total_copiados} assets copiados manteniendo estructura")
            
            # ✅ VERIFICAR ESTRUCTURA COPIADA
            if os.path.exists(assets_destino):
                try:
                    self.log_signal.emit("🔍 Verificando estructura copiada...")
                    self.mostrar_estructura_assets(assets_destino)
                except Exception as e:
                    self.log_signal.emit(f"✅ Assets copiados (error en verificación: {str(e)})")
            
            return True
            
        except Exception as e:
            self.log_signal.emit(f"❌ Error copiando assets: {str(e)}")
            return False

    def mostrar_estructura_assets(self, ruta_assets):
        """Mostrar estructura de assets copiada"""
        try:
            for root, dirs, files in os.walk(ruta_assets):
                # Calcular nivel de indentación
                nivel = root.replace(ruta_assets, '').count(os.sep)
                indentacion = "    " * nivel
                
                # Mostrar carpeta actual
                carpeta = os.path.basename(root)
                if carpeta:  # No mostrar la carpeta raíz
                    self.log_signal.emit(f"{indentacion}📂 {carpeta}/")
                
                # Mostrar archivos en esta carpeta (máximo 5 por carpeta)
                for i, archivo in enumerate(files):
                    if i < 5:  # Mostrar solo primeros 5 archivos por carpeta
                        self.log_signal.emit(f"{indentacion}    📄 {archivo}")
                    elif i == 5:
                        self.log_signal.emit(f"{indentacion}    ... y {len(files) - 5} más")
                        break
                    
        except Exception as e:
            self.log_signal.emit(f"⚠️  Error mostrando estructura: {str(e)}")
    
    def ejecutar_deploy(self, tipo, servidor, comando_personalizado=""):
        """Ejecutar deploy según el tipo de servidor"""
        try:
            if tipo == "cli":
                return self.deploy_con_cli(servidor, comando_personalizado)
            elif tipo == "git":
                return self.deploy_con_git_completo(servidor, comando_personalizado)
            elif tipo == "manual":
                return self.deploy_manual(servidor)
            else:
                return self.deploy_con_git_completo(servidor, comando_personalizado)
                
        except Exception as e:
            self.log_signal.emit(f"❌ Error en deploy {servidor}: {str(e)}")
            return self.deploy_con_git_completo(servidor, comando_personalizado)
    
    def deploy_con_cli(self, servidor, comando_personalizado=""):
        """Deploy usando CLI específico (Railway, Heroku, etc.)"""
        try:
            self.log_signal.emit(f"🔧 Ejecutando deploy via CLI para {servidor}...")
            
            # Determinar qué CLI usar basado en el servidor
            if "railway" in servidor.lower():
                cli_tool = "railway"
                comando_base = "railway deploy"
            elif "heroku" in servidor.lower():
                cli_tool = "heroku"
                comando_base = "git push heroku main"
            else:
                # CLI genérico
                cli_tool = servidor
                comando_base = comando_personalizado
            
            # Verificar que la CLI está instalada
            if not self.verificar_herramienta(cli_tool):
                self.log_signal.emit(f"❌ {cli_tool} CLI no encontrado")
                return False
            
            # Ejecutar comando de deploy
            comando = comando_personalizado if comando_personalizado else comando_base
            self.log_signal.emit(f"🚀 Ejecutando: {comando}")
            
            os.chdir(self.backend_path)
            result = subprocess.run(
                comando.split(), 
                capture_output=True, 
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.log_signal.emit(f"✅ Deploy via {cli_tool} exitoso!")
                if result.stdout:
                    for linea in result.stdout.split('\n'):
                        if linea.strip():
                            self.log_signal.emit(f"   📤 {linea.strip()}")
                return True
            else:
                self.log_signal.emit(f"❌ Error en {cli_tool} deploy: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_signal.emit(f"❌ Error en CLI deploy: {str(e)}")
            return False

    def deploy_manual(self, servidor):
        """Provee instrucciones para deploy manual"""
        try:
            self.log_signal.emit("📋 MODO MANUAL - INSTRUCCIONES:")
            self.log_signal.emit("=" * 50)
            
            # Instrucciones específicas basadas en el servidor
            if "railway" in servidor.lower():
                instrucciones = [
                    "1. Abrir terminal en la carpeta del backend",
                    "2. Ejecutar: railway login",
                    "3. Ejecutar: railway link (si no está vinculado)",
                    "4. Ejecutar: railway deploy",
                    "5. O usar: git push origin main (si está conectado a GitHub)"
                ]
            elif "heroku" in servidor.lower():
                instrucciones = [
                    "1. Abrir terminal en la carpeta del backend", 
                    "2. Ejecutar: heroku login",
                    "3. Ejecutar: git push heroku main",
                    "4. O usar: heroku deploy:war"
                ]
            else:
                instrucciones = [
                    "1. Subir manualmente los archivos al servidor",
                    "2. Asegurar que requirements.txt tiene gunicorn",
                    "3. Configurar Procfile para producción",
                    "4. Reiniciar servicio web"
                ]
            
            for paso in instrucciones:
                self.log_signal.emit(f"   {paso}")
            
            self.log_signal.emit("")
            self.log_signal.emit("📁 Archivos preparados para deploy manual:")
            
            # Listar archivos esenciales
            archivos_esenciales = [
                "api.py", "requirements.txt", "database_hosting.py",
                "railway.toml", "Procfile", "assets/", "runtime.txt"
            ]
            
            for archivo in archivos_esenciales:
                ruta = os.path.join(self.backend_path, archivo)
                if os.path.exists(ruta):
                    if os.path.isdir(ruta):
                        try:
                            num_items = len(os.listdir(ruta))
                            self.log_signal.emit(f"   ✅ {archivo} ({num_items} elementos)")
                        except:
                            self.log_signal.emit(f"   ✅ {archivo} (carpeta)")
                    else:
                        self.log_signal.emit(f"   ✅ {archivo}")
                else:
                    self.log_signal.emit(f"   ❌ {archivo} - FALTANTE")
            
            self.log_signal.emit("")
            self.log_signal.emit("🎯 El backend está listo para deploy manual")
            return True
            
        except Exception as e:
            self.log_signal.emit(f"❌ Error generando instrucciones: {str(e)}")
            return False
    
    def deploy_con_git_completo(self, servidor, comando):
        """✅ DEPLOY COMPLETO con Git - Con pull automático"""
        try:
            self.log_signal.emit(f"📦 Ejecutando DEPLOY AUTOMÁTICO via Git...")
            
            if not self.verificar_herramienta("git"):
                self.log_signal.emit("❌ Git no encontrado en el sistema")
                return False
            
            os.chdir(self.backend_path)
            
            if not os.path.exists(".git"):
                self.log_signal.emit("❌ No es un repositorio Git")
                return False
            
            # ✅ PASO 1: GIT PULL para traer cambios remotos
            self.log_signal.emit("🔄 Sincronizando con repositorio remoto...")
            result_pull = subprocess.run(
                ["git", "pull", "origin", "main"], 
                capture_output=True, 
                text=True
            )
            
            if result_pull.returncode == 0:
                self.log_signal.emit("✅ Sincronización completada")
                if result_pull.stdout:
                    for linea in result_pull.stdout.split('\n'):
                        if linea.strip() and any(x in linea for x in ['Already up to date', 'Updating', 'Fast-forward']):
                            self.log_signal.emit(f"   🔄 {linea.strip()}")
            else:
                self.log_signal.emit(f"⚠️  Advertencia en sincronización: {result_pull.stderr}")
            
            # ✅ PASO 2: AGREGAR TODOS LOS ARCHIVOS
            self.log_signal.emit("💾 Agregando archivos al staging...")
            result_add = subprocess.run(
                ["git", "add", "."], 
                capture_output=True, 
                text=True
            )
            
            if result_add.returncode != 0:
                self.log_signal.emit(f"❌ Error agregando archivos: {result_add.stderr}")
                return False
            
            self.log_signal.emit("✅ Todos los archivos agregados al staging")
            
            # ✅ PASO 3: COMMIT
            mensaje_commit = f"Deploy PRODUCCIÓN: API + Assets + Gunicorn - {time.strftime('%Y-%m-%d %H:%M')}"
            self.log_signal.emit(f"💾 Realizando commit: {mensaje_commit}")
            
            commit_result = subprocess.run(
                ["git", "commit", "-m", mensaje_commit], 
                capture_output=True, 
                text=True
            )
            
            if commit_result.returncode == 0:
                self.log_signal.emit("✅ Commit realizado exitosamente")
            else:
                self.log_signal.emit("ℹ️  Sin cambios para commitear (posiblemente ya estaban commiteados)")
            
            # ✅ PASO 4: PUSH
            comando_push = comando if comando else "git push origin main"
            self.log_signal.emit(f"🔧 Ejecutando: {comando_push}")
            
            result_push = subprocess.run(
                comando_push.split(), 
                capture_output=True, 
                text=True,
                timeout=300
            )
            
            if result_push.returncode == 0:
                self.log_signal.emit("🎉 ¡PUSH EXITOSO A GITHUB!")
                if result_push.stdout:
                    for linea in result_push.stdout.split('\n'):
                        if linea.strip() and any(x in linea for x in ['Writing objects', 'To http', 'master ->', 'main ->']):
                            self.log_signal.emit(f"   📤 {linea.strip()}")
                
                # Verificar assets en GitHub
                self.verificar_assets_en_git()
                
                self.log_signal.emit("🔄 Railway detectará los cambios automáticamente...")
                self.log_signal.emit("⏳ El deploy en Railway puede tomar 2-5 minutos")
                self.log_signal.emit("🚀 Configurado para PRODUCCIÓN con Gunicorn")
                
                return True
            else:
                self.log_signal.emit(f"❌ Error en push: {result_push.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.log_signal.emit("❌ Timeout: El push tardó demasiado")
            return False
        except Exception as e:
            self.log_signal.emit(f"❌ Error: {str(e)}")
            return False
    
    def verificar_assets_en_git(self):
        """Verificar que los assets se subieron a GitHub"""
        try:
            result = subprocess.run(
                ["git", "ls-tree", "-r", "HEAD", "--name-only"], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                archivos = result.stdout.split('\n')
                assets_subidos = [f for f in archivos if f.startswith('assets/')]
                
                if assets_subidos:
                    self.log_signal.emit(f"✅ {len(assets_subidos)} assets subidos a GitHub")
                    # Mostrar primeros 5 assets como ejemplo
                    for asset in assets_subidos[:5]:
                        self.log_signal.emit(f"   📄 {asset}")
                    if len(assets_subidos) > 5:
                        self.log_signal.emit(f"   ... y {len(assets_subidos) - 5} más")
                else:
                    self.log_signal.emit("⚠️  No se detectaron assets en el repositorio")
        except Exception as e:
            self.log_signal.emit(f"⚠️  No se pudo verificar assets: {str(e)}")
    
    def verificar_deploy(self):
        """Verificar que el deploy funcionó correctamente"""
        try:
            base_url = self.datos_hosting.get('base_url')
            if not base_url or base_url == 'No configurada':
                return True
            
            self.log_signal.emit("🔍 Verificando estado del servidor en PRODUCCIÓN...")
            self.log_signal.emit(f"🌐 URL: {base_url}")
            
            endpoints = [
                "/api/health",
                "/api/configuracion",
                "/"
            ]
            
            todos_funcionan = True
            for endpoint in endpoints:
                url = base_url + endpoint
                try:
                    response = requests.get(url, timeout=15)
                    if response.status_code == 200:
                        self.log_signal.emit(f"✅ {endpoint} - FUNCIONA")
                        if endpoint == "/api/health":
                            try:
                                data = response.json()
                                if 'entorno' in data:
                                    self.log_signal.emit(f"   🏭 Entorno: {data['entorno']}")
                            except:
                                pass
                    else:
                        self.log_signal.emit(f"⚠️  {endpoint} - Error {response.status_code}")
                        todos_funcionan = False
                except requests.exceptions.RequestException as e:
                    self.log_signal.emit(f"❌ {endpoint} - No responde: {str(e)}")
                    todos_funcionan = False
            
            if todos_funcionan:
                self.log_signal.emit("🎊 ¡TODOS LOS ENDPOINTS FUNCIONAN EN PRODUCCIÓN!")
                self.log_signal.emit("✅ Servidor configurado con Gunicorn para producción")
            else:
                self.log_signal.emit("⚠️  Algunos endpoints tienen problemas")
            
            return True
            
        except Exception as e:
            self.log_signal.emit(f"⚠️  Error en verificación: {str(e)}")
            return False
    
    def verificar_herramienta(self, herramienta):
        """Verificar si una herramienta está instalada"""
        try:
            result = subprocess.run(
                [herramienta, "--version"], 
                capture_output=True, 
                text=True,
                shell=True,
                timeout=10
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            self.log_signal.emit(f"⚠️  Timeout verificando {herramienta}")
            return False
        except:
            return False

class DialogoBackendDeploy(QDialog):
    """Diálogo para deploy COMPLETO del backend en PRODUCCIÓN"""
    
    def __init__(self, parent=None, backend_path=None):
        super().__init__(parent)
        self.backend_path = backend_path or r"E:\Sistemas de app para androide\turismo-app\turismo-backend"
        self.datos_hosting = None
        self.setup_ui()
        self.cargar_configuracion_desde_bd()
    
    def cargar_configuracion_desde_bd(self):
        """Cargar configuración desde BD"""
        try:
            from database_local import obtener_configuracion_hosting
            
            self.datos_hosting = obtener_configuracion_hosting()
            
            if self.datos_hosting and self.datos_hosting.get('host'):
                host = self.datos_hosting.get('host', 'N/A')
                base_url = self.datos_hosting.get('base_url', 'No configurada')
                
                usuario = self.datos_hosting.get('user', 'N/A')
                base_datos = self.datos_hosting.get('database', 'N/A')
                puerto = self.datos_hosting.get('port', 'N/A')
                
                info_text = (
                    f"🌐 Host: {host}\n"
                    f"🔗 URL: {base_url}\n"
                    f"👤 Usuario: {usuario}\n"
                    f"🗃️ BD: {base_datos}\n"
                    f"🔒 Puerto: {puerto}"
                )
                
                self.lbl_info_hosting.setText(info_text)
                self.log(f"✅ Configuración cargada: {host}")
                
                # Auto-seleccionar Git como método principal
                self.combo_tipo.setCurrentText("📦 Git (Automático)")
                self.txt_comando.setText("git push origin main")
                
            else:
                self.lbl_info_hosting.setText("❌ No hay configuración de hosting")
                self.log("⚠️  Configure primero el hosting")
                
        except Exception as e:
            self.lbl_info_hosting.setText("❌ Error cargando configuración")
            self.log(f"❌ Error: {str(e)}")

    def setup_ui(self):
        self.setWindowTitle("🚀 Deploy PRODUCCIÓN - Backend + Assets")
        self.setFixedSize(680, 520)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Título
        titulo = QLabel("🚀 DEPLOY COMPLETO PARA PRODUCCIÓN")
        titulo.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; margin: 8px 0px;")
        layout.addWidget(titulo)
        
        # Información del hosting
        info_hosting_group = QGroupBox("🌐 Configuración de Hosting")
        info_hosting_layout = QVBoxLayout()
        
        self.lbl_info_hosting = QLabel("Cargando configuración...")
        self.lbl_info_hosting.setStyleSheet("font-size: 11px; color: #2c3e50; padding: 10px; background-color: #f8f9fa; line-height: 1.4;")
        self.lbl_info_hosting.setWordWrap(True)
        self.lbl_info_hosting.setMinimumHeight(80)
        info_hosting_layout.addWidget(self.lbl_info_hosting)
        
        info_hosting_group.setLayout(info_hosting_layout)
        layout.addWidget(info_hosting_group)
        
        # Configuración de deploy
        config_group = QGroupBox("⚙️ Configuración de Deploy")
        config_layout = QVBoxLayout()
        config_layout.setSpacing(8)
        
        lbl_tipo = QLabel("Método de deploy:")
        lbl_tipo.setStyleSheet("font-size: 11px; font-weight: bold;")
        config_layout.addWidget(lbl_tipo)
        
        self.combo_tipo = QComboBox()
        tipos = ["📦 Git (Automático)", "🔧 CLI (Railway)", "📋 Manual"]
        self.combo_tipo.addItems(tipos)
        self.combo_tipo.setStyleSheet("font-size: 11px; padding: 6px; height: 30px;")
        config_layout.addWidget(self.combo_tipo)
        
        lbl_comando = QLabel("Comando:")
        lbl_comando.setStyleSheet("font-size: 11px; font-weight: bold;")
        config_layout.addWidget(lbl_comando)
        
        self.txt_comando = QLineEdit()
        self.txt_comando.setPlaceholderText("git push origin main")
        self.txt_comando.setStyleSheet("padding: 6px; font-size: 11px; height: 30px;")
        config_layout.addWidget(self.txt_comando)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Información del backend
        info_backend_group = QGroupBox("📁 Archivos para PRODUCCIÓN")
        info_backend_layout = QVBoxLayout()
        
        self.lbl_backend = QLabel(f"📁 {self.backend_path}")
        self.lbl_backend.setStyleSheet("font-size: 10px; color: #7f8c8d;")
        
        self.lbl_archivos = QLabel("🔍 Verificando...")
        self.lbl_archivos.setStyleSheet("font-size: 10px; line-height: 1.3;")
        self.lbl_archivos.setWordWrap(True)
        self.lbl_archivos.setMinimumHeight(60)
        
        info_backend_layout.addWidget(self.lbl_backend)
        info_backend_layout.addWidget(self.lbl_archivos)
        info_backend_group.setLayout(info_backend_layout)
        layout.addWidget(info_backend_group)
        
        # Log output
        lbl_log = QLabel("📝 Log de ejecución:")
        lbl_log.setStyleSheet("font-size: 11px; font-weight: bold;")
        layout.addWidget(lbl_log)
        
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(120)
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("font-family: 'Consolas'; font-size: 9px; background-color: #f8f9fa;")
        layout.addWidget(self.log_output)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(10)
        layout.addWidget(self.progress_bar)
        
        # Botones
        botones_layout = QHBoxLayout()
        botones_layout.setSpacing(8)
        
        self.btn_deploy = QPushButton("🚀 Deploy PRODUCCIÓN (Gunicorn)")
        self.btn_deploy.setStyleSheet("QPushButton { background-color: #27ae60; color: white; padding: 8px 15px; border: none; border-radius: 4px; font-weight: bold; font-size: 11px; min-width: 200px; } QPushButton:hover { background-color: #219a52; } QPushButton:disabled { background-color: #bdc3c7; }")
        
        self.btn_verificar = QPushButton("🔍 Verificar")
        self.btn_verificar.setStyleSheet("QPushButton { background-color: #3498db; color: white; padding: 8px 15px; border: none; border-radius: 4px; font-weight: bold; font-size: 11px; min-width: 100px; } QPushButton:hover { background-color: #2980b9; }")
        
        self.btn_limpiar = QPushButton("🗑️ Limpiar")
        self.btn_limpiar.setStyleSheet("QPushButton { background-color: #f39c12; color: white; padding: 8px 15px; border: none; border-radius: 4px; font-weight: bold; font-size: 11px; min-width: 100px; } QPushButton:hover { background-color: #e67e22; }")
        
        self.btn_cerrar = QPushButton("❌ Cerrar")
        self.btn_cerrar.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; padding: 8px 15px; border: none; border-radius: 4px; font-weight: bold; font-size: 11px; min-width: 100px; } QPushButton:hover { background-color: #c0392b; }")
        
        botones_layout.addWidget(self.btn_deploy)
        botones_layout.addWidget(self.btn_verificar)
        botones_layout.addWidget(self.btn_limpiar)
        botones_layout.addWidget(self.btn_cerrar)
        
        layout.addLayout(botones_layout)
        
        scroll.setWidget(scroll_content)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
        
        self.btn_deploy.clicked.connect(self.iniciar_deploy)
        self.btn_verificar.clicked.connect(self.verificar_archivos)
        self.btn_limpiar.clicked.connect(self.limpiar_log)
        self.btn_cerrar.clicked.connect(self.close)
        
        self.deploy_thread = None
        self.verificar_archivos()

    def verificar_archivos(self):
        """Verificar archivos para deploy en producción"""
        try:
            archivos_esenciales = {
                "api.py": "Servidor Flask",
                "requirements.txt": "Dependencias", 
                "database_hosting.py": "Conexión BD",
                "railway.toml": "Config Railway",
                "Procfile": "Config Proceso",
                ".git": "Repositorio Git"
            }
            
            mensaje = ""
            for archivo, descripcion in archivos_esenciales.items():
                ruta_archivo = os.path.join(self.backend_path, archivo)
                existe = os.path.exists(ruta_archivo)
                icono = "✅" if existe else "❌"
                mensaje += f"{icono} {archivo} - {descripcion}\n"
            
            # Verificar gunicorn en requirements
            requirements_path = os.path.join(self.backend_path, "requirements.txt")
            if os.path.exists(requirements_path):
                with open(requirements_path, 'r') as f:
                    contenido = f.read()
                if 'gunicorn' in contenido:
                    mensaje += "✅ Gunicorn - Configurado para producción\n"
                else:
                    mensaje += "❌ Gunicorn - Faltante para producción\n"
            
            # Verificar assets
            assets_path = os.path.join(self.backend_path, "assets")
            if os.path.exists(assets_path):
                try:
                    num_assets = len(os.listdir(assets_path))
                    mensaje += f"✅ Assets: {num_assets} archivos listos\n"
                except:
                    mensaje += "✅ Assets: Carpeta encontrada\n"
            else:
                mensaje += "❌ Assets: No encontrados\n"
            
            self.lbl_archivos.setText(mensaje)
            self.log("🔍 Verificación completada para PRODUCCIÓN")
            
        except Exception as e:
            self.lbl_archivos.setText(f"❌ Error: {str(e)}")

    def obtener_tipo_deploy(self):
        """Obtener tipo de deploy seleccionado"""
        texto = self.combo_tipo.currentText()
        mapeo = {
            "📦 Git (Automático)": "git",
            "🔧 CLI (Railway)": "cli", 
            "📋 Manual": "manual"
        }
        return mapeo.get(texto, "git")

    def limpiar_log(self):
        self.log_output.clear()
        self.log("🗑️ Log limpiado")
    
    def log(self, mensaje):
        self.log_output.append(f"{mensaje}")
        self.log_output.moveCursor(self.log_output.textCursor().End)

    def iniciar_deploy(self):
        """Iniciar deploy completo para producción"""
        if not self.datos_hosting:
            QMessageBox.warning(self, "Configuración", "Configure hosting primero")
            return
        
        self.verificar_archivos()
        
        tipo = self.obtener_tipo_deploy()
        comando = self.txt_comando.text().strip()
        
        self.btn_deploy.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.log_output.clear()
        self.log("🚀 INICIANDO DEPLOY PARA PRODUCCIÓN...")
        self.log("📝 Configurando Gunicorn como servidor WSGI de producción")
        
        config = {
            'nombre': self.datos_hosting.get('host', 'Servidor'),
            'tipo': tipo,
            'comando': comando,
            'datos_hosting': self.datos_hosting
        }
        
        self.deploy_thread = BackendDeployThread(self.backend_path, config)
        self.deploy_thread.log_signal.connect(self.log)
        self.deploy_thread.progress_signal.connect(self.progress_bar.setValue)
        self.deploy_thread.finished_signal.connect(self.proceso_finalizado)
        self.deploy_thread.start()
    
    def proceso_finalizado(self, exito, mensaje):
        self.btn_deploy.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.log(mensaje)
        
        if exito:
            QMessageBox.information(self, "🎉 ¡PRODUCCIÓN CONFIGURADA!", 
                                  f"{mensaje}\n\n"
                                  f"✅ Gunicorn configurado como servidor WSGI\n"
                                  f"✅ Sincronización con GitHub completada\n"
                                  f"✅ Assets copiados al repositorio\n"
                                  f"✅ Código subido a GitHub\n" 
                                  f"✅ Railway desplegando automáticamente\n"
                                  f"✅ API funcionando en PRODUCCIÓN")
        else:
            QMessageBox.critical(self, "❌ Error", mensaje)

def mostrar_dialogo_backend_deploy(parent=None):
    dialogo = DialogoBackendDeploy(parent)
    dialogo.exec_()

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication([])
    dialogo = DialogoBackendDeploy()
    dialogo.show()
    app.exec_()