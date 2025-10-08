# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QApplication, QMessageBox
from ventana_principal import VentanaPrincipal
from ventana_licencia import VentanaLicencia
from database_local import inicializar_base_datos_local  # ← SOLO local
from database_hosting import inicializar_base_datos_hosting  # ← NUEVO: solo inicialización
from licencia import LicenciaManager
import sys


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 1) Inicializa SOLO base de datos LOCAL (licencia + datos_hosting)
    if not inicializar_base_datos_local():  # ← Esto ahora puede mostrar diálogos
        QMessageBox.critical(None, "Error", "No se pudo inicializar la base de datos local")
        sys.exit(1)

    # 2) Valida licencia (usa DB local)
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

    # 3) INICIALIZAR BASE DE DATOS DEL HOSTING (automáticamente obtiene configuración)
    print("Inicializando base de datos del hosting...")
    if not inicializar_base_datos_hosting():
        QMessageBox.critical(None, "Error de Hosting", 
                           "No se pudo inicializar la base de datos del hosting.\n"
                           "Verifique:\n"
                           "- La configuración en 'datos_hosting' sea correcta\n"
                           "- Su conexión a internet esté activa\n"
                           "- El servidor hosting esté disponible")
        sys.exit(1)
    else:
        print("[SUCCESS] Base de datos del hosting inicializada correctamente")

    # 4) Abrir principal
    ventana_principal = VentanaPrincipal()
    ventana_principal.show()
    
    print("[SUCCESS] Aplicación iniciada correctamente")
    sys.exit(app.exec())