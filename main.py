# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QApplication, QMessageBox
from ventana_principal import VentanaPrincipal
from ventana_licencia import VentanaLicencia
from database import inicializar_base_datos
from licencia import LicenciaManager
import sys


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 1) Inicializa tablas
    inicializar_base_datos()

    # 2) Valida licencia
    manager = LicenciaManager()
    ok, mensaje = manager.validar_licencia()

    if not ok:
        QMessageBox.critical(None, "Licencia", mensaje)
        dlg = VentanaLicencia(modo="activar")
        if dlg.exec_() == 0:  # canceló
            sys.exit(1)
        # Revalidar después de cerrar la ventana de licencia
        ok, mensaje = manager.validar_licencia()
        if not ok:
            QMessageBox.critical(None, "Licencia", mensaje)
            sys.exit(1)
    else:
        if "vencerá" in mensaje:
            QMessageBox.information(None, "Aviso de licencia", mensaje)

    # 3) Abrir principal
    ventana_principal = VentanaPrincipal()
    ventana_principal.show()
    sys.exit(app.exec())
