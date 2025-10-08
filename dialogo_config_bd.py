# dialogo_config_bd.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QSpinBox
from PyQt5.QtCore import Qt
import mysql.connector
from mysql.connector import Error

class DialogoConfigBD(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Base de Datos")
        self.setFixedSize(400, 350)  # ✅ Aumentado para base_url
        self.setWindowModality(Qt.ApplicationModal)
        
        self.layout = QVBoxLayout()
        
        # Campos de configuración
        self.layout.addWidget(QLabel("Host:"))
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("ej: localhost o 192.168.1.100")
        self.layout.addWidget(self.host_input)
        
        self.layout.addWidget(QLabel("Puerto:"))
        self.puerto_input = QSpinBox()
        self.puerto_input.setRange(1, 65535)
        self.puerto_input.setValue(3306)
        self.layout.addWidget(self.puerto_input)
        
        self.layout.addWidget(QLabel("Usuario:"))
        self.usuario_input = QLineEdit()
        self.usuario_input.setPlaceholderText("ej: root")
        self.layout.addWidget(self.usuario_input)
        
        self.layout.addWidget(QLabel("Contraseña:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.password_input)
        
        self.layout.addWidget(QLabel("Base de Datos:"))
        self.bd_input = QLineEdit()
        self.bd_input.setPlaceholderText("ej: turismo_db")
        self.layout.addWidget(self.bd_input)
        
        # ✅ NUEVO CAMPO: Base URL
        self.layout.addWidget(QLabel("Base URL (API):"))
        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("ej: https://tudominio.com o http://localhost:5000")
        self.layout.addWidget(self.base_url_input)
        
        # Botones
        botones_layout = QHBoxLayout()
        
        self.btn_probar = QPushButton("Probar Conexión")
        self.btn_probar.clicked.connect(self.probar_conexion)
        botones_layout.addWidget(self.btn_probar)
        
        self.btn_guardar = QPushButton("Guardar")
        self.btn_guardar.clicked.connect(self.guardar_configuracion)
        botones_layout.addWidget(self.btn_guardar)
        
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        botones_layout.addWidget(self.btn_cancelar)
        
        self.layout.addLayout(botones_layout)
        self.setLayout(self.layout)
        
        # Valores por defecto
        self.host_input.setText("localhost")
        self.usuario_input.setText("root")
        self.bd_input.setText("turismo_db")
        self.base_url_input.setText("http://localhost:5000")  # ✅ VALOR POR DEFECTO
    
    def probar_conexion(self):
        """Prueba la conexión con los datos ingresados"""
        host = self.host_input.text().strip()
        usuario = self.usuario_input.text().strip()
        password = self.password_input.text()
        base_datos = self.bd_input.text().strip()
        puerto = self.puerto_input.value()
        
        if not all([host, usuario, base_datos]):
            QMessageBox.warning(self, "Campos incompletos", "Complete todos los campos obligatorios.")
            return
        
        try:
            conexion = mysql.connector.connect(
                host=host,
                user=usuario,
                password=password,
                database=base_datos,
                port=puerto,
                connect_timeout=10
            )
            
            if conexion.is_connected():
                conexion.close()
                QMessageBox.information(self, "Conexión exitosa", "¡Conexión a la base de datos exitosa!")
                return True
                
        except Error as e:
            QMessageBox.critical(self, "Error de conexión", f"No se pudo conectar:\n{str(e)}")
            return False
    
    def guardar_configuracion(self):
        """Guarda la configuración en la tabla datos_hosting (LOCAL)"""
        if not self.probar_conexion():
            return
        
        host = self.host_input.text().strip()
        usuario = self.usuario_input.text().strip()
        password = self.password_input.text()
        base_datos = self.bd_input.text().strip()
        puerto = self.puerto_input.value()
        base_url = self.base_url_input.text().strip()  # ✅ NUEVO CAMPO
        
        try:
            # Importar la función de guardado desde database_local
            from database_local import guardar_configuracion_hosting
            
            # ✅ PASAR base_url a la función
            if guardar_configuracion_hosting(host, usuario, password, base_datos, puerto, base_url, self):
                QMessageBox.information(self, "Configuración guardada", 
                                    "Configuración del hosting guardada exitosamente.")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "No se pudo guardar la configuración.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración:\n{str(e)}")