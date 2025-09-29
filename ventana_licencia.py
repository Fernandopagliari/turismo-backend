# ventana_licencia.py
from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5 import uic
import os
from datetime import datetime, timedelta
from licencia import LicenciaManager
from hardware_id import obtener_hardware_id
from database import conectar_base_datos   # 🔹 Conexión centralizada a MySQL


class VentanaLicencia(QDialog):
    def __init__(self, modo="activar"):
        super().__init__()
        # Ruta absoluta y robusta al archivo .ui
        ruta_ui = os.path.join(
            os.path.dirname(__file__),   # carpeta actual: src/backend
            "interfaz",                  # subcarpeta
            "ventana_licencia.ui"        # archivo .ui
        )

        if not os.path.exists(ruta_ui):
            raise FileNotFoundError(f"No se encontró el archivo UI en: {ruta_ui}")

        uic.loadUi(ruta_ui, self)

        # Conexión al gestor de licencias
        self.licencia = LicenciaManager()

        # Configuración de campos
        self.lineSerial.setReadOnly(False)
        self.lineClave.setEchoMode(self.lineClave.Password)  # Ocultar clave
        self.modo = modo

        # Eventos
        self.checkFechaManual.toggled.connect(self.toggle_fecha_manual)
        self.btnActivar.clicked.connect(lambda: self.activar_o_extender("activar"))
        self.btnExtender.clicked.connect(lambda: self.activar_o_extender("extender"))

        # Configurar vista inicial según el modo
        self.configurar_modo()

    def toggle_fecha_manual(self, checked):
        """Habilita o deshabilita fecha manual/días de validez."""
        self.dateExpiracion.setEnabled(checked)
        self.spinDiasValidez.setEnabled(not checked)

    def configurar_modo(self):
        """Configura la ventana dependiendo si es activación o extensión."""
        conexion = conectar_base_datos()
        if not conexion:
            QMessageBox.critical(self, "Error", "No se pudo conectar a la base de datos.")
            self.close()
            return

        cursor = conexion.cursor()
        cursor.execute("SELECT serial, fecha_expiracion, hardware_id FROM licencia LIMIT 1")
        datos = cursor.fetchone()
        cursor.close()
        conexion.close()

        if self.modo == "activar":
            # Activación inicial
            self.lineSerial.setReadOnly(False)
            self.btnActivar.setEnabled(True)
            self.btnExtender.setEnabled(False)
            self.spinDiasValidez.setEnabled(True)
            self.dateExpiracion.setEnabled(False)

            # Clave no es necesaria en activación
            self.lineClave.setVisible(False)
            self.labelClave.setVisible(False)

        elif self.modo == "extender" and datos:
            serial_guardado, _, hardware_guardado = datos
            self.lineSerial.setText(serial_guardado)
            self.lineSerial.setReadOnly(True)

            # Clave requerida para extender
            self.lineClave.setVisible(True)
            self.labelClave.setVisible(True)
            self.btnActivar.setEnabled(False)
            self.btnExtender.setEnabled(True)

            # Validar hardware
            hardware_actual = obtener_hardware_id()
            if hardware_guardado != hardware_actual:
                QMessageBox.critical(self, "Error", "Esta licencia no corresponde a este equipo.")
                self.close()

    def activar_o_extender(self, modo):
        """Acciones para activar o extender licencia."""
        serial = self.lineSerial.text().strip()

        if not serial:
            QMessageBox.warning(self, "Error", "Debe ingresar un número de serie.")
            return

        if modo == "extender":
            clave_ingresada = self.lineClave.text().strip()

            if not clave_ingresada:
                QMessageBox.warning(self, "Error", "Debe ingresar la clave para extender la licencia.")
                return

            # Calcular nueva fecha
            if self.checkFechaManual.isChecked():
                nueva_fecha = self.dateExpiracion.date().toString("yyyy-MM-dd")
            else:
                dias_validez = self.spinDiasValidez.value()
                nueva_fecha = (datetime.now() + timedelta(days=dias_validez)).strftime("%Y-%m-%d")

            ok, mensaje = self.licencia.extender_licencia(nueva_fecha, serial, clave_ingresada)

        else:  # Activación
            fecha_manual = self.dateExpiracion.date().toString("yyyy-MM-dd") if self.checkFechaManual.isChecked() else None
            dias_validez = None if self.checkFechaManual.isChecked() else self.spinDiasValidez.value()

            hardware_actual = obtener_hardware_id()

            ok, mensaje = self.licencia.activar_licencia(
                serial,
                clave=None,
                fecha_exp_manual=fecha_manual,
                dias_validez=dias_validez,
                hardware_id=hardware_actual
            )

        # Mostrar resultado
        if ok:
            QMessageBox.information(self, "Licencia", mensaje)
            self.accept()   # ✅ en lugar de self.close()
        else:
            QMessageBox.critical(self, "Error", mensaje)


