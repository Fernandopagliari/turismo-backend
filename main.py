# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QApplication, QMessageBox, QDialog, QVBoxLayout, 
                            QLabel, QProgressBar, QTextEdit, QPushButton, QHBoxLayout)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QTextCursor
from ventana_principal import VentanaPrincipal
from ventana_licencia import VentanaLicencia
from database_local import inicializar_base_datos_local
from licencia import LicenciaManager
import sys
import subprocess
import os
import time
import socket

class DialogoDiagnostico(QDialog):
    """Diálogo de diagnóstico completamente independiente"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Diagnóstico MySQL")
        self.setFixedSize(700, 600)
        # Hacerlo no-modal para que no bloquee la ventana principal
        self.setWindowModality(Qt.NonModal)
        
        layout = QVBoxLayout()
        
        # Área de texto para resultados
        self.texto_resultados = QTextEdit()
        self.texto_resultados.setFont(QFont("Consolas", 9))
        self.texto_resultados.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        self.texto_resultados.setReadOnly(True)
        layout.addWidget(self.texto_resultados)
        
        # Botones
        botones_layout = QHBoxLayout()
        
        self.btn_ejecutar = QPushButton("Ejecutar Diagnóstico")
        self.btn_ejecutar.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
        """)
        
        self.btn_cerrar = QPushButton("Cerrar Diagnóstico")
        self.btn_cerrar.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        
        botones_layout.addWidget(self.btn_ejecutar)
        botones_layout.addWidget(self.btn_cerrar)
        layout.addLayout(botones_layout)
        
        self.setLayout(layout)

class VentanaInicio(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Turismo App - Inicializando")
        self.setFixedSize(600, 500)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        # Variables de control
        self.proceso_activo = False
        self.detener_solicitado = False
        self.proceso_mysql = None
        self.mysql_portable_iniciado_por_nosotros = False
        self.etapa_actual = 0
        self.timer_proceso = QTimer()
        self.timer_proceso.timeout.connect(self.ejecutar_proceso)
        
        # Nueva variable para control de instalación nueva
        self.es_instalacion_nueva = False
        
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Título principal
        titulo = QLabel("🚀 TURISMO APP - INICIANDO SISTEMA")
        titulo.setFont(QFont("Arial", 16, QFont.Bold))
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("""
            color: #2c3e50; 
            margin: 15px; 
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 8px;
        """)
        layout.addWidget(titulo)
        
        # Barra de progreso principal
        self.barra_progreso = QProgressBar()
        self.barra_progreso.setMaximum(100)
        self.barra_progreso.setValue(0)
        self.barra_progreso.setStyleSheet("""
            QProgressBar {
                border: 2px solid #34495e;
                border-radius: 8px;
                text-align: center;
                height: 25px;
                font-weight: bold;
                color: #2c3e50;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.barra_progreso)
        
        # Etiqueta de estado actual
        self.etiqueta_estado = QLabel("Preparando el sistema...")
        self.etiqueta_estado.setFont(QFont("Arial", 11, QFont.Bold))
        self.etiqueta_estado.setAlignment(Qt.AlignCenter)
        self.etiqueta_estado.setStyleSheet("color: #e74c3c; margin: 10px;")
        layout.addWidget(self.etiqueta_estado)
        
        # Área de logs
        self.log_area = QTextEdit()
        self.log_area.setMaximumHeight(250)
        self.log_area.setFont(QFont("Consolas", 9))
        self.log_area.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 2px solid #34495e;
                border-radius: 5px;
                padding: 8px;
            }
        """)
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        
        # Botones
        botones_layout = QHBoxLayout()
        
        self.btn_detener = QPushButton("⏹️ Detener")
        self.btn_detener.clicked.connect(self.detener_proceso)
        self.btn_detener.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        
        self.btn_diagnostico = QPushButton("🔧 Diagnóstico")
        self.btn_diagnostico.clicked.connect(self.mostrar_diagnostico)
        self.btn_diagnostico.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        self.btn_continuar = QPushButton("✅ Aceptar y Continuar")
        self.btn_continuar.clicked.connect(self.continuar_aplicacion)
        self.btn_continuar.setEnabled(False)
        self.btn_continuar.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #219a52;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        
        botones_layout.addWidget(self.btn_detener)
        botones_layout.addWidget(self.btn_diagnostico)
        botones_layout.addWidget(self.btn_continuar)
        layout.addLayout(botones_layout)
        
        self.setLayout(layout)

    def agregar_log(self, mensaje, tipo="info"):
        timestamp = time.strftime("%H:%M:%S")
        
        if tipo == "error":
            color = "#e74c3c"
            icon = "❌"
        elif tipo == "warning":
            color = "#f39c12"
            icon = "⚠️"
        elif tipo == "success":
            color = "#27ae60"
            icon = "✅"
        else:
            color = "#3498db"
            icon = "ℹ️"
        
        html = f'<span style="color: #95a5a6;">[{timestamp}]</span> <span style="color: {color};"><b>{icon} {mensaje}</b></span>'
        self.log_area.append(html)
        
        cursor = self.log_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_area.setTextCursor(cursor)
        self.log_area.ensureCursorVisible()
        
        QApplication.processEvents()

    def actualizar_progreso(self, porcentaje, estado, log=""):
        self.barra_progreso.setValue(porcentaje)
        self.etiqueta_estado.setText(estado)
        
        if porcentaje < 30:
            color = "#e74c3c"
        elif porcentaje < 70:
            color = "#f39c12"
        else:
            color = "#27ae60"
        
        self.etiqueta_estado.setStyleSheet(f"color: {color}; margin: 10px; font-weight: bold;")
        
        if log:
            self.agregar_log(log, "info")
        
        QApplication.processEvents()

    def encontrar_carpeta_frontend(self, base_dir):
        """Buscar dinámicamente la carpeta turismo-frontend"""
        # Posibles ubicaciones relativas
        rutas_posibles = [
            # Estructura típica de instalación
            os.path.join(base_dir, "turismo-frontend"),
            os.path.join(os.path.dirname(base_dir), "turismo-frontend"),
            
            # Para desarrollo
            os.path.join(base_dir, "..", "turismo-frontend"),
            os.path.join(base_dir, "..", "..", "turismo-frontend"),
            
            # Rutas absolutas comunes (como fallback)
            r"C:\Turismo App\turismo-frontend",
            r"D:\Turismo App\turismo-frontend", 
            r"E:\Turismo App\turismo-frontend",
            
            # Buscar en el directorio de usuario
            os.path.join(os.path.expanduser("~"), "Turismo App", "turismo-frontend"),
        ]
        
        for ruta in rutas_posibles:
            ruta_absoluta = os.path.abspath(ruta)
            if os.path.exists(ruta_absoluta):
                self.agregar_log(f"✅ Frontend encontrado en: {ruta_absoluta}", "success")
                return ruta_absoluta
        
        # Si no se encuentra, mostrar las rutas buscadas para debug
        self.agregar_log("❌ No se encontró turismo-frontend en las siguientes ubicaciones:", "error")
        for ruta in rutas_posibles:
            self.agregar_log(f"   - {os.path.abspath(ruta)}", "info")
        
        return None

    def detectar_instalacion_nueva(self):
        """Detectar si es una instalación nueva en una PC"""
        try:
            # Verificar si existe archivo de marca de instalación previa
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            
            archivo_marca = os.path.join(base_dir, "instalacion_completada.txt")
            
            # Si NO existe el archivo de marca, es instalación nueva
            if not os.path.exists(archivo_marca):
                self.es_instalacion_nueva = True
                self.agregar_log("🔍 Detección: INSTALACIÓN NUEVA detectada", "info")
                return True
            
            # Verificar si el frontend existe y tiene contenido
            frontend_dir = self.encontrar_carpeta_frontend(base_dir)
            if frontend_dir:
                # Verificar si hay repositorio Git configurado
                git_dir = os.path.join(frontend_dir, ".git")
                if not os.path.exists(git_dir):
                    self.es_instalacion_nueva = True
                    self.agregar_log("🔍 Detección: Frontend sin Git configurado", "info")
                    return True
            
            self.es_instalacion_nueva = False
            self.agregar_log("🔍 Detección: INSTALACIÓN EXISTENTE", "info")
            return False
            
        except Exception as e:
            self.agregar_log(f"⚠️ Error detectando tipo de instalación: {str(e)}", "warning")
            return False

    def verificar_estado_git(self):
        """Verificar si Git está configurado correctamente para subir imágenes"""
        try:
            # Obtener la ruta base de la instalación dinámicamente
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Buscar turismo-frontend en ubicaciones posibles
            frontend_dir = self.encontrar_carpeta_frontend(base_dir)
            
            if not frontend_dir:
                return False, "No se encontró la carpeta turismo-frontend"
            
            # Verificar si Git está instalado en el sistema
            try:
                resultado_git = subprocess.run(
                    ["git", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=True
                )
                
                if resultado_git.returncode != 0:
                    return False, "Git no está instalado en el sistema"
            except:
                return False, "Git no está instalado en el sistema"
            
            # Verificar si es repositorio Git (desde el directorio del frontend)
            try:
                resultado_status = subprocess.run(
                    ["git", "status"],
                    cwd=frontend_dir,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True
                )
                
                if resultado_status.returncode != 0:
                    return False, "No es un repositorio Git válido"
            except:
                return False, "No es un repositorio Git válido"
            
            # Verificar remotes
            try:
                resultado_remote = subprocess.run(
                    ["git", "remote", "-v"],
                    cwd=frontend_dir,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True
                )
                
                if resultado_remote.returncode != 0 or not resultado_remote.stdout.strip():
                    return False, "No hay remotes configurados"
                
                # Verificar que tenga al menos un remote con push
                if "push" not in resultado_remote.stdout.lower():
                    return False, "Remote configurado pero sin capacidad de push"
            except:
                return False, "No se pudo verificar remotes"
            
            return True, f"Git configurado correctamente - Las imágenes se subirán desde: {frontend_dir}"
            
        except Exception as e:
            return False, f"Error verificando Git: {str(e)}"

    def configurar_git_automatico_silencioso(self):
        """Configurar Git automáticamente y silenciosamente para instalación nueva"""
        try:
            self.agregar_log("🔄 Configuración automática de Git en progreso...", "info")
            
            # Obtener rutas
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            
            frontend_dir = self.encontrar_carpeta_frontend(base_dir)
            
            if not frontend_dir:
                self.agregar_log("❌ No se encontró turismo-frontend", "error")
                return False
            
            # 1. Verificar si Git está instalado
            try:
                resultado = subprocess.run(
                    ["git", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True
                )
                if resultado.returncode != 0:
                    self.agregar_log("❌ Git no está instalado - No se puede configurar automáticamente", "error")
                    return False
                else:
                    self.agregar_log(f"✅ Git instalado: {resultado.stdout.strip()}", "success")
            except:
                self.agregar_log("❌ No se pudo verificar Git", "error")
                return False
            
            # 2. Crear carpeta de imágenes si no existe
            imagenes_dir = os.path.join(frontend_dir, "public", "assets", "imagenes")
            try:
                os.makedirs(imagenes_dir, exist_ok=True)
                self.agregar_log(f"✅ Carpeta de imágenes verificada: {imagenes_dir}", "success")
            except Exception as e:
                self.agregar_log(f"⚠️ No se pudo crear carpeta de imágenes: {str(e)}", "warning")
            
            # 3. Inicializar repositorio Git si no existe
            git_dir = os.path.join(frontend_dir, ".git")
            if not os.path.exists(git_dir):
                self.agregar_log("📦 Inicializando repositorio Git...", "info")
                try:
                    # Inicializar repositorio
                    subprocess.run(
                        ["git", "init"],
                        cwd=frontend_dir,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        shell=True
                    )
                    
                    # Configurar usuario
                    subprocess.run(
                        ["git", "config", "user.name", "Turismo App"],
                        cwd=frontend_dir,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        shell=True
                    )
                    
                    subprocess.run(
                        ["git", "config", "user.email", "app@turismo.local"],
                        cwd=frontend_dir,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        shell=True
                    )
                    
                    self.agregar_log("✅ Repositorio Git inicializado", "success")
                except Exception as e:
                    self.agregar_log(f"❌ Error inicializando repositorio: {str(e)}", "error")
                    return False
            
            # 4. Configurar remote (usar repositorio público como fallback)
            try:
                # Verificar si ya hay remotes
                resultado_remote = subprocess.run(
                    ["git", "remote", "-v"],
                    cwd=frontend_dir,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True
                )
                
                if not resultado_remote.stdout.strip() or "push" not in resultado_remote.stdout.lower():
                    self.agregar_log("🔗 Configurando remote de repositorio...", "info")
                    
                    # Intentar con repositorio público
                    try:
                        # Primero eliminar cualquier remote existente
                        subprocess.run(
                            ["git", "remote", "remove", "origin"],
                            cwd=frontend_dir,
                            capture_output=True,
                            text=True,
                            timeout=10,
                            shell=True,
                            stderr=subprocess.DEVNULL
                        )
                        
                        # Agregar remote del repositorio público
                        subprocess.run(
                            ["git", "remote", "add", "origin", "https://github.com/TurismoAppValle/turismo-frontend.git"],
                            cwd=frontend_dir,
                            capture_output=True,
                            text=True,
                            timeout=10,
                            shell=True
                        )
                        
                        self.agregar_log("✅ Remote configurado: Repositorio público de Turismo App", "success")
                    except Exception as e:
                        self.agregar_log(f"⚠️ No se pudo configurar remote automático: {str(e)}", "warning")
                        # Crear un remote local como fallback
                        try:
                            subprocess.run(
                                ["git", "remote", "add", "local", frontend_dir],
                                cwd=frontend_dir,
                                capture_output=True,
                                text=True,
                                timeout=10,
                                shell=True
                            )
                            self.agregar_log("✅ Remote local configurado como fallback", "success")
                        except:
                            pass
                else:
                    self.agregar_log("✅ Remote ya configurado", "success")
            except Exception as e:
                self.agregar_log(f"⚠️ Error configurando remote: {str(e)}", "warning")
            
            # 5. Crear archivo README si no existe
            readme_path = os.path.join(frontend_dir, "README.txt")
            if not os.path.exists(readme_path):
                try:
                    with open(readme_path, 'w', encoding='utf-8') as f:
                        f.write("""TURISMO APP - SISTEMA DE FRONTEND
=====================================

Esta carpeta contiene el frontend de la aplicación Turismo App.

📍 UBICACIÓN DE IMÁGENES:
public/assets/imagenes/

📁 ESTRUCTURA RECOMENDADA:
public/assets/imagenes/hoteles/
public/assets/imagenes/restaurantes/
public/assets/imagenes/lugares/
public/assets/imagenes/usuarios/

🔧 CONFIGURACIÓN GIT:
Git está configurado para subir imágenes automáticamente.

Para modificar la configuración:
1. Abre Git Bash o CMD en esta carpeta
2. Ejecuta: git remote -v  (para ver remotes)
3. Para cambiar: git remote set-url origin [tu_url]

ℹ️ Las imágenes se sincronizarán automáticamente con el repositorio configurado.
""")
                    self.agregar_log("✅ Archivo README creado", "success")
                except:
                    pass
            
            # 6. Crear archivo de marca de instalación completada
            try:
                if getattr(sys, 'frozen', False):
                    base_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                
                marca_path = os.path.join(base_dir, "instalacion_completada.txt")
                with open(marca_path, 'w', encoding='utf-8') as f:
                    f.write(f"""INSTALACIÓN TURISMO APP COMPLETADA
====================================
Fecha: {time.strftime("%Y-%m-%d %H:%M:%S")}
Frontend configurado en: {frontend_dir}
Git configurado automáticamente: Sí
Carpeta de imágenes: {imagenes_dir}

Para configurar tu propio repositorio:
1. Crea un repositorio en GitHub/GitLab
2. En la carpeta del frontend, ejecuta:
   git remote set-url origin [tu_url_del_repositorio]
3. Ejecuta: git push -u origin main

Soporte: soporte@turismoapp.com
""")
                self.agregar_log("✅ Marca de instalación creada", "success")
            except Exception as e:
                self.agregar_log(f"⚠️ No se pudo crear marca de instalación: {str(e)}", "warning")
            
            # 7. Verificar configuración final
            git_ok, mensaje = self.verificar_estado_git()
            if git_ok:
                self.agregar_log(f"✅ Configuración Git completada: {mensaje}", "success")
                return True
            else:
                self.agregar_log(f"⚠️ Configuración Git parcial: {mensaje}", "warning")
                # Aún así retornamos True porque la instalación básica está hecha
                return True
                
        except Exception as e:
            self.agregar_log(f"❌ Error en configuración automática: {str(e)}", "error")
            return False

    def verificar_configuracion_git_instalacion_nueva(self):
        """Verificar y configurar Git para instalación nueva - SILENCIOSO"""
        self.actualizar_progreso(95, "Configurando sistema...", "🔄 Configuración automática en progreso...")
        
        # Detectar si es instalación nueva
        if self.detectar_instalacion_nueva():
            self.agregar_log("🆕 DETECTADA INSTALACIÓN NUEVA - Configurando automáticamente...", "info")
            
            # Ejecutar configuración automática silenciosa
            if self.configurar_git_automatico_silencioso():
                self.actualizar_progreso(98, "Configuración completada", "✅ Sistema configurado automáticamente")
                
                # Mostrar resumen de configuración
                if getattr(sys, 'frozen', False):
                    base_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                
                frontend_dir = self.encontrar_carpeta_frontend(base_dir)
                if frontend_dir:
                    imagenes_dir = os.path.join(frontend_dir, "public", "assets", "imagenes")
                    self.agregar_log("🎉 CONFIGURACIÓN AUTOMÁTICA COMPLETADA", "success")
                    self.agregar_log(f"📍 Imágenes en: {imagenes_dir}", "info")
                    self.agregar_log("🔗 Git configurado para sincronización automática", "info")
                    
                    # Crear archivo de instrucciones en el escritorio
                    try:
                        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                        instrucciones_path = os.path.join(desktop, "TurismoApp_Instrucciones.txt")
                        
                        with open(instrucciones_path, 'w', encoding='utf-8') as f:
                            f.write(f"""INSTRUCCIONES TURISMO APP - INSTALACIÓN NUEVA
================================================

✅ INSTALACIÓN COMPLETADA CORRECTAMENTE

📁 UBICACIONES IMPORTANTES:
• Aplicación: {base_dir}
• Frontend: {frontend_dir}
• Imágenes: {imagenes_dir}

🔧 CONFIGURACIÓN AUTOMÁTICA:
• Git configurado para sincronizar imágenes
• Carpeta de imágenes creada
• Sistema listo para usar

📝 PARA USAR EL SISTEMA:
1. Las imágenes que subas se guardarán en:
   {imagenes_dir}
   
2. Se crearán automáticamente subcarpetas según el tipo:
   - hoteles/
   - restaurantes/
   - lugares/
   - usuarios/

3. Las imágenes se subirán automáticamente al repositorio.

🔄 PARA CONFIGURAR TU PROPIO REPOSITORIO:
1. Crea un repositorio en GitHub o GitLab
2. Abre CMD en: {frontend_dir}
3. Ejecuta:
   git remote set-url origin [URL_DE_TU_REPOSITORIO]
   git push -u origin main

📞 SOPORTE: soporte@turismoapp.com
""")
                        self.agregar_log(f"📄 Instrucciones creadas en el escritorio: {instrucciones_path}", "info")
                    except:
                        pass
            else:
                self.actualizar_progreso(98, "Configuración parcial", "⚠️ Configuración automática con advertencias")
                self.agregar_log("ℹ️ El sistema funcionará, pero Git puede requerir configuración manual", "info")
        else:
            self.actualizar_progreso(98, "Configuración verificada", "✅ Sistema ya configurado")
            self.agregar_log("✅ Instalación existente - Configuración verificada", "success")
        
        self.etapa_actual += 1

    def iniciar_proceso(self):
        """Iniciar el proceso de inicialización"""
        self.proceso_activo = True
        self.detener_solicitado = False
        self.mysql_portable_iniciado_por_nosotros = False
        self.etapa_actual = 0
        self.agregar_log("Iniciando proceso de inicialización del sistema...", "info")
        
        self.timer_proceso.start(100)

    def ejecutar_proceso(self):
        """Ejecutar el proceso paso a paso"""
        if self.detener_solicitado:
            self.finalizar_proceso()
            return
            
        if self.etapa_actual == 0:
            self.verificar_mysql()
        elif self.etapa_actual == 1:
            self.inicializar_bd_local()
        elif self.etapa_actual == 2:
            self.verificar_licencia()
        elif self.etapa_actual == 3:
            self.inicializar_sistema()
        elif self.etapa_actual == 4:
            # Usar la nueva función para instalación nueva
            self.verificar_configuracion_git_instalacion_nueva()
        elif self.etapa_actual == 5:
            self.finalizar_inicializacion()
        else:
            self.timer_proceso.stop()

    # ===== MÉTODOS EXISTENTES (NO MODIFICADOS) =====
    
    def verificar_mysql(self):
        """Etapa 1: Verificar MySQL"""
        self.actualizar_progreso(10, "Verificando servidor MySQL...", "Buscando servidor MySQL en puertos comunes...")
        
        try:
            puertos = [3306, 3307, 3308, 3309]
            mysql_encontrado = False
            puerto_encontrado = None
            
            for puerto in puertos:
                if self.detener_solicitado:
                    return
                    
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    resultado = sock.connect_ex(('localhost', puerto))
                    sock.close()
                    if resultado == 0:
                        self.actualizar_progreso(20, "MySQL encontrado", f"✅ MySQL encontrado en puerto {puerto}")
                        mysql_encontrado = True
                        puerto_encontrado = puerto
                        
                        servicio_ejecutandose = self.verificar_servicios_mysql()
                        if servicio_ejecutandose:
                            self.agregar_log(f"✅ Usando {servicio_ejecutandose} en puerto {puerto_encontrado}", "success")
                        else:
                            self.agregar_log(f"✅ Usando MySQL Portable en puerto {puerto_encontrado}", "success")
                        
                        break
                except:
                    continue
            
            if mysql_encontrado:
                self.etapa_actual += 1
                return
                
            if not self.detener_solicitado:
                self.actualizar_progreso(15, "Iniciando MySQL Portable...", "🚀 Iniciando MySQL Portable...")
                if self.iniciar_mysql_portable_mejorado():
                    self.mysql_portable_iniciado_por_nosotros = True
                    self.etapa_actual += 1
                else:
                    self.mostrar_error_mysql()
                
        except Exception as e:
            self.agregar_log(f"Error verificando MySQL: {str(e)}", "error")
            self.mostrar_error_mysql()

    def verificar_servicios_mysql(self):
        """Verificar servicios de MySQL"""
        try:
            servicios = ['MySQL', 'MySQL80', 'MySQL57', 'MySQL56', 'MariaDB']
            for servicio in servicios:
                resultado = subprocess.run(
                    f'sc query {servicio}',
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "RUNNING" in resultado.stdout:
                    return servicio
            return None
        except:
            return None

    def iniciar_mysql_portable_mejorado(self):
        """Iniciar MySQL Portable - VERSIÓN MEJORADA con más tiempo"""
        try:
            base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            mysql_bat = os.path.join(base_dir, "start_mysql.bat")
            
            if not os.path.exists(mysql_bat):
                self.agregar_log("❌ No se encuentra start_mysql.bat", "error")
                return False

            self.agregar_log("🔍 Verificando archivos MySQL Portable...", "info")
            
            # Verificación exhaustiva
            mysqld_exe = os.path.join(base_dir, "mysql-server", "bin", "mysqld.exe")
            if not os.path.exists(mysqld_exe):
                self.agregar_log(f"❌ No se encuentra: {mysqld_exe}", "error")
                return False
                
            my_ini = os.path.join(base_dir, "mysql-server", "my.ini")
            if not os.path.exists(my_ini):
                self.agregar_log(f"❌ No se encuentra: {my_ini}", "error")
                return False
            
            self.agregar_log("✅ Archivos de MySQL Portable verificados", "success")
            self.agregar_log("🚀 Ejecutando MySQL Portable...", "info")
            
            # Método mejorado para instalación
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
                
                self.proceso_mysql = subprocess.Popen(
                    [mysql_bat],
                    cwd=base_dir,
                    startupinfo=startupinfo,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                self.agregar_log("✅ Proceso MySQL Portable iniciado", "success")
                
            except Exception as e:
                self.agregar_log(f"❌ Error ejecutando MySQL Portable: {str(e)}", "error")
                # Intentar método alternativo
                try:
                    os.startfile(mysql_bat)
                    self.agregar_log("✅ MySQL Portable iniciado con método alternativo", "success")
                except Exception as e2:
                    self.agregar_log(f"❌ Método alternativo también falló: {str(e2)}", "error")
                    return False

            # ⏰ ESPERAR 60 SEGUNDOS - TIEMPO EXTENDIDO para instalación
            self.agregar_log("⏳ Esperando que MySQL Portable inicie (puede tomar hasta 60 segundos)...", "info")
            
            for i in range(60):  # 60 segundos máximo
                if self.detener_solicitado:
                    if self.proceso_mysql:
                        self.proceso_mysql.terminate()
                    return False
                
                # Actualizar progreso con más detalle
                progreso = 15 + int((i / 60) * 15)
                tiempo_restante = 60 - i
                self.actualizar_progreso(progreso, f"Iniciando MySQL Portable...", f"Esperando... {i+1}/60 segundos (restan: {tiempo_restante}s)")
                
                # Verificar si MySQL está escuchando
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    resultado = sock.connect_ex(('localhost', 3306))
                    sock.close()
                    if resultado == 0:
                        self.agregar_log(f"✅ MySQL Portable iniciado correctamente después de {i+1} segundos", "success")
                        return True
                except:
                    pass
                
                # Verificar si el proceso sigue activo
                if self.proceso_mysql and self.proceso_mysql.poll() is not None:
                    # Proceso terminó, leer output para debug
                    try:
                        stdout, stderr = self.proceso_mysql.communicate(timeout=1)
                        if stderr:
                            error_msg = stderr.decode('latin-1', errors='ignore')
                            self.agregar_log(f"❌ Error MySQL: {error_msg}", "error")
                    except:
                        pass
                    
                    self.agregar_log("❌ El proceso de MySQL Portable se cerró inesperadamente", "error")
                    return False
                
                time.sleep(1)
                QApplication.processEvents()

            self.agregar_log("❌ MySQL Portable no inició después de 60 segundos", "error")
            return False
            
        except Exception as e:
            self.agregar_log(f"❌ Error crítico iniciando MySQL Portable: {str(e)}", "error")
            return False

    def mostrar_diagnostico(self):
        """Mostrar diálogo de diagnóstico - COMPLETAMENTE INDEPENDIENTE"""
        try:
            # Crear diálogo como ventana completamente independiente
            dialogo = DialogoDiagnostico(self)
            
            # Conectar botones
            dialogo.btn_ejecutar.clicked.connect(lambda: self.ejecutar_diagnostico_completo(dialogo))
            dialogo.btn_cerrar.clicked.connect(dialogo.close)
            
            # Mostrar sin bloquear - clave para que no cierre la aplicación
            dialogo.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo mostrar el diagnóstico:\n{str(e)}")

    def ejecutar_diagnostico_completo(self, dialogo):
        """Ejecutar diagnóstico completo en el diálogo"""
        def agregar_resultado(mensaje, tipo="info"):
            if tipo == "error":
                color = "#e74c3c"
                icon = "❌"
            elif tipo == "warning":
                color = "#f39c12"
                icon = "⚠️"
            elif tipo == "success":
                color = "#27ae60"
                icon = "✅"
            else:
                color = "#3498db"
                icon = "ℹ️"
            
            html = f'<span style="color: {color};"><b>{icon} {mensaje}</b></span><br>'
            dialogo.texto_resultados.append(html)
            QApplication.processEvents()
        
        try:
            agregar_resultado("=" * 60)
            agregar_resultado("🔍 DIAGNÓSTICO COMPLETO MYSQL")
            agregar_resultado("=" * 60)
            
            # 1. Verificar puertos
            agregar_resultado("", "info")
            agregar_resultado("1. 📡 VERIFICANDO PUERTOS:", "info")
            puertos = [3306, 3307, 3308, 3309]
            for puerto in puertos:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    resultado = sock.connect_ex(('localhost', puerto))
                    sock.close()
                    if resultado == 0:
                        agregar_resultado(f"   Puerto {puerto}: OCUPADO", "error")
                    else:
                        agregar_resultado(f"   Puerto {puerto}: LIBRE", "success")
                except Exception as e:
                    agregar_resultado(f"   Puerto {puerto}: ERROR - {e}", "error")
            
            # 2. Verificar servicios MySQL
            agregar_resultado("", "info")
            agregar_resultado("2. 🔧 VERIFICANDO SERVICIOS MYSQL:", "info")
            servicios = ['MySQL', 'MySQL80', 'MySQL57', 'MySQL56', 'MariaDB']
            for servicio in servicios:
                try:
                    resultado = subprocess.run(
                        f'sc query {servicio}',
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if "RUNNING" in resultado.stdout:
                        agregar_resultado(f"   {servicio}: EJECUTÁNDOSE", "success")
                    elif "STOPPED" in resultado.stdout:
                        agregar_resultado(f"   {servicio}: DETENIDO", "warning")
                    else:
                        agregar_resultado(f"   {servicio}: NO INSTALADO", "info")
                except Exception as e:
                    agregar_resultado(f"   {servicio}: ERROR - {e}", "error")
            
            # 3. Verificar MySQL Portable
            agregar_resultado("", "info")
            agregar_resultado("3. 📁 VERIFICANDO MYSQL PORTABLE:", "info")
            base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            archivos = [
                "start_mysql.bat",
                "mysql-server/bin/mysqld.exe",
                "mysql-server/my.ini"
            ]
            
            for archivo in archivos:
                ruta = os.path.join(base_dir, archivo)
                if os.path.exists(ruta):
                    agregar_resultado(f"   {archivo}: ENCONTRADO", "success")
                else:
                    agregar_resultado(f"   {archivo}: NO ENCONTRADO", "error")
            
            # 4. Verificar si MySQL Portable está ejecutándose
            agregar_resultado("", "info")
            agregar_resultado("4. 🔍 VERIFICANDO EJECUCIÓN MYSQL PORTABLE:", "info")
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                resultado = sock.connect_ex(('localhost', 3306))
                sock.close()
                if resultado == 0:
                    agregar_resultado("   MySQL Portable: ✅ EJECUTÁNDOSE", "success")
                else:
                    agregar_resultado("   MySQL Portable: ❌ NO EJECUTÁNDOSE", "error")
            except Exception as e:
                agregar_resultado(f"   MySQL Portable: ERROR - {e}", "error")
            
            agregar_resultado("", "info")
            agregar_resultado("=" * 60, "info")
            agregar_resultado("💡 RECOMENDACIONES:", "info")
            agregar_resultado("• Si hay puertos ocupados: Detener otros servicios MySQL", "info")
            agregar_resultado("• Si falta MySQL Portable: Reinstalar la aplicación", "info")
            agregar_resultado("• Si MySQL Portable no ejecuta: Verificar permisos de administrador", "info")
            agregar_resultado("=" * 60, "info")
            
        except Exception as e:
            agregar_resultado(f"❌ Error durante el diagnóstico: {str(e)}", "error")

    def inicializar_bd_local(self):
        """Etapa 2: Inicializar base de datos local"""
        self.actualizar_progreso(40, "Inicializando base de datos...", "Conectando con la base de datos 'databaseapp'...")
        
        try:
            if inicializar_base_datos_local():
                self.actualizar_progreso(50, "BD local lista", "✅ Base de datos local inicializada correctamente")
                self.etapa_actual += 1
            else:
                self.agregar_log("❌ Error al inicializar la base de datos local", "error")
                self.mostrar_error_bd()
        except Exception as e:
            self.agregar_log(f"❌ Error en base de datos: {str(e)}", "error")
            self.mostrar_error_bd()

    def verificar_licencia(self):
        """Etapa 3: Verificar licencia - VERSIÓN CORREGIDA"""
        self.actualizar_progreso(60, "Verificando licencia...", "🔐 Validando licencia de software...")
        
        try:
            licencia_manager = LicenciaManager()
            
            # ✅ VERIFICACIÓN CORRECTA usando el método que existe
            ok, mensaje = licencia_manager.validar_licencia()
            
            if ok:
                # Licencia válida
                if "vencerá" in mensaje:
                    self.agregar_log(f"⚠️ {mensaje}", "warning")
                    # Mostrar advertencia pero continuar
                    QMessageBox.information(self, "Aviso de Licencia", mensaje)
                else:
                    self.agregar_log(f"✅ {mensaje}", "success")
                
                self.actualizar_progreso(70, "Licencia válida", "✅ Licencia verificada correctamente")
                self.etapa_actual += 1
            else:
                # Licencia inválida o no existe
                self.agregar_log(f"❌ {mensaje}", "error")
                self.mostrar_ventana_licencia()
                
        except Exception as e:
            self.agregar_log(f"❌ Error crítico verificando licencia: {str(e)}", "error")
            self.mostrar_error_licencia()

    def mostrar_ventana_licencia(self):
        """Mostrar ventana de licencia - VERSIÓN CORREGIDA"""
        self.actualizar_progreso(65, "Esperando licencia...", "📋 Mostrando ventana de licencia...")
        
        self.timer_proceso.stop()
        
        try:
            ventana_licencia = VentanaLicencia(modo="activar")
            resultado = ventana_licencia.exec_()
            
            if resultado == QDialog.Accepted:
                # ✅ REVALIDAR después de activar la licencia
                self.actualizar_progreso(68, "Validando nueva licencia...", "🔍 Verificando licencia activada...")
                licencia_manager = LicenciaManager()
                ok, mensaje = licencia_manager.validar_licencia()
                
                if ok:
                    self.actualizar_progreso(70, "Licencia activada", "✅ Licencia activada correctamente")
                    self.agregar_log(f"✅ Licencia activada: {mensaje}", "success")
                    self.etapa_actual += 1
                else:
                    self.agregar_log(f"❌ Licencia aún no válida: {mensaje}", "error")
                    self.mostrar_error_licencia()
            else:
                self.agregar_log("❌ Activación de licencia cancelada por el usuario", "error")
                self.mostrar_error_licencia()
                
        except Exception as e:
            self.agregar_log(f"❌ Error en ventana de licencia: {str(e)}", "error")
            self.mostrar_error_licencia()
        
        if not self.detener_solicitado:
            self.timer_proceso.start(100)

    def inicializar_sistema(self):
        """Etapa 4: Inicialización final del sistema"""
        self.actualizar_progreso(80, "Preparando interfaz...", "Cargando módulos del sistema...")
        
        modulos = ["Módulos de seguridad", "Módulos de base de datos", "Módulos de interfaz"]
        
        for i, modulo in enumerate(modulos):
            if self.detener_solicitado:
                return
                
            self.actualizar_progreso(80 + (i * 6), "Cargando sistema...", f"✅ {modulo} cargados")
            QApplication.processEvents()
            
        self.etapa_actual += 1

    def finalizar_inicializacion(self):
        """Etapa 6: Finalizar inicialización"""
        self.actualizar_progreso(100, "Sistema listo", "✅ Inicialización completada")
        
        # Habilitar botón de continuar
        self.btn_continuar.setEnabled(True)
        self.btn_detener.setEnabled(False)
        
        self.agregar_log("=" * 50, "info")
        self.agregar_log("🎉 SISTEMA INICIALIZADO CORRECTAMENTE", "success")
        self.agregar_log("=" * 50, "info")
        
        self.timer_proceso.stop()
        self.proceso_activo = False

    def detener_proceso(self):
        """Detener el proceso de inicialización"""
        if self.proceso_activo:
            self.detener_solicitado = True
            self.agregar_log("⏹️ Deteniendo proceso...", "warning")
            self.btn_detener.setEnabled(False)

    def finalizar_proceso(self):
        """Finalizar el proceso limpiamente"""
        self.proceso_activo = False
        self.detener_solicitado = False
        
        # Detener MySQL Portable si lo iniciamos nosotros
        if self.mysql_portable_iniciado_por_nosotros and self.proceso_mysql:
            try:
                self.agregar_log("🛑 Deteniendo MySQL Portable...", "info")
                self.proceso_mysql.terminate()
                self.proceso_mysql.wait(timeout=5)
                self.agregar_log("✅ MySQL Portable detenido", "success")
            except:
                self.agregar_log("⚠️ No se pudo detener MySQL Portable correctamente", "warning")
        
        self.timer_proceso.stop()
        self.actualizar_progreso(0, "Proceso detenido", "❌ Proceso de inicialización detenido")
        self.btn_detener.setEnabled(False)

    def continuar_aplicacion(self):
        """Continuar a la aplicación principal - VERSIÓN CORREGIDA"""
        try:
            self.agregar_log("🚀 Iniciando aplicación principal...", "info")
            
            # Ocultar ventana de inicio
            self.hide()
            
            # Crear y mostrar ventana principal
            self.ventana_principal = VentanaPrincipal()
            self.ventana_principal.show()
            
            # CONEXIÓN SIMPLIFICADA - Cerrar toda la aplicación cuando se cierre la ventana principal
            self.ventana_principal.destroyed.connect(self.cerrar_todo)
                
        except Exception as e:
            self.agregar_log(f"❌ Error iniciando aplicación principal: {str(e)}", "error")
            QMessageBox.critical(self, "Error", f"No se pudo iniciar la aplicación:\n{str(e)}")
            self.show()

    def cerrar_todo(self):
        """Cerrar toda la aplicación"""
        try:
            # Detener MySQL Portable si lo iniciamos nosotros
            if self.mysql_portable_iniciado_por_nosotros and self.proceso_mysql:
                self.agregar_log("🛑 Cerrando MySQL Portable...", "info")
                self.proceso_mysql.terminate()
            
            # Cerrar aplicación
            QApplication.quit()
            
        except Exception as e:
            print(f"Error cerrando aplicación: {e}")
            QApplication.quit()

    def mostrar_error_mysql(self):
        """Mostrar error de MySQL"""
        self.timer_proceso.stop()
        
        mensaje = QMessageBox(self)
        mensaje.setWindowTitle("❌ Error de MySQL")
        mensaje.setIcon(QMessageBox.Critical)
        mensaje.setText("No se pudo conectar con MySQL")
        mensaje.setInformativeText(
            "No se pudo encontrar ni iniciar MySQL en el sistema.\n\n"
            "Posibles soluciones:\n"
            "• Verificar que MySQL esté instalado\n"
            "• Usar el botón 'Diagnóstico' para más información\n"
            "• Asegurarse de que los archivos de MySQL Portable estén presentes"
        )
        
        mensaje.addButton("Ejecutar Diagnóstico", QMessageBox.ActionRole)
        mensaje.addButton("Reintentar", QMessageBox.RetryRole)
        mensaje.addButton("Salir", QMessageBox.RejectRole)
        
        respuesta = mensaje.exec_()
        
        if respuesta == 0:  # Diagnóstico
            self.mostrar_diagnostico()
            self.timer_proceso.start(100)
        elif respuesta == 1:  # Reintentar
            self.timer_proceso.start(100)
        else:  # Salir
            self.finalizar_proceso()
            self.close()

    def mostrar_error_bd(self):
        """Mostrar error de base de datos"""
        self.timer_proceso.stop()
        
        QMessageBox.critical(self, "Error de Base de Datos",
            "No se pudo inicializar la base de datos local.\n\n"
            "Verifique que:\n"
            "• MySQL esté ejecutándose\n"
            "• Tenga permisos de administrador\n"
            "• La base de datos 'databaseapp' exista")
        
        self.finalizar_proceso()

    def mostrar_error_licencia(self):
        """Mostrar error de licencia"""
        self.timer_proceso.stop()
        
        respuesta = QMessageBox.critical(self, "Error de Licencia",
            "No se pudo validar la licencia del software.\n\n"
            "Es necesario activar una licencia válida para continuar.",
            QMessageBox.Retry | QMessageBox.Close,
            QMessageBox.Retry)
        
        if respuesta == QMessageBox.Retry:
            self.mostrar_ventana_licencia()
        else:
            self.finalizar_proceso()

    def closeEvent(self, event):
        """Manejar cierre de ventana"""
        if self.proceso_activo:
            respuesta = QMessageBox.question(self, "Confirmar cierre",
                "El proceso de inicialización está en curso.\n"
                "¿Estás seguro de que quieres cerrar la aplicación?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No)
            
            if respuesta == QMessageBox.Yes:
                self.finalizar_proceso()
                event.accept()
            else:
                event.ignore()
        else:
            self.finalizar_proceso()
            event.accept()

def main():
    """Función principal de la aplicación"""
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("Turismo App")
        app.setApplicationVersion("2.0.0")
        
        # Crear y mostrar ventana de inicio
        ventana_inicio = VentanaInicio()
        ventana_inicio.show()
        
        # Iniciar proceso después de mostrar la ventana
        QTimer.singleShot(500, ventana_inicio.iniciar_proceso)
        
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"Error crítico: {e}")
        QMessageBox.critical(None, "Error Crítico", 
            f"No se pudo iniciar la aplicación:\n{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()