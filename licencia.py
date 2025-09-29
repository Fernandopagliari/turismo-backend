# -*- coding: utf-8 -*-
# src/backend/licencia.py
from datetime import datetime, timedelta
from database import conectar_base_datos
from hardware_id import obtener_hardware_id
from seguridad import fernet  # ✅ usamos el fernet central
import bcrypt

class LicenciaManager:
    # Si querés exigir una "clave maestra" para extender:
    CLAVE_PREDEFINIDA_HASH = "$2b$12$0Y.cJPYfkc451kfRnpxwD.sKGrdnAd5tcWT36vboeCnzYMl.79r2K"

    def __init__(self):
        self.crear_tabla()

    def crear_tabla(self):
        cn = conectar_base_datos()
        if not cn:
            return
        cur = cn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS licencia (
                id INT AUTO_INCREMENT PRIMARY KEY,
                serial VARCHAR(100) NOT NULL,
                clave VARCHAR(255) NOT NULL,
                fecha_activacion DATE NOT NULL,
                fecha_expiracion TEXT NOT NULL,
                hardware_id VARCHAR(255)
            ) ENGINE=InnoDB;
        """)
        cn.commit()
        cur.close()
        cn.close()

    def activar_licencia(self, serial, clave=None, fecha_exp_manual=None, dias_validez=365, hardware_id=None):
        cn = conectar_base_datos()
        if not cn:
            return False, "No se pudo conectar a la base de datos."

        cur = cn.cursor()
        fecha_activacion = datetime.now().strftime("%Y-%m-%d")

        # Definir fecha de expiración
        if fecha_exp_manual:
            try:
                datetime.strptime(fecha_exp_manual, "%Y-%m-%d")
                fecha_exp = fecha_exp_manual
            except ValueError:
                cur.close(); cn.close()
                return False, "Formato de fecha inválido. Usa YYYY-MM-DD."
        else:
            fecha_exp = (datetime.now() + timedelta(days=dias_validez)).strftime("%Y-%m-%d")

        # Encriptar fecha
        fecha_exp_enc = fernet.encrypt(fecha_exp.encode()).decode()

        if not hardware_id:
            hardware_id = obtener_hardware_id()

        # Guardar (pisamos cualquier licencia previa)
        cur.execute("DELETE FROM licencia")
        cur.execute("""
            INSERT INTO licencia (serial, clave, fecha_activacion, fecha_expiracion, hardware_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (serial, self.CLAVE_PREDEFINIDA_HASH, fecha_activacion, fecha_exp_enc, hardware_id))

        cn.commit()
        cur.close(); cn.close()
        return True, f"Licencia activada hasta {fecha_exp}"

    def validar_licencia(self):
        cn = conectar_base_datos()
        if not cn:
            return False, "No se pudo conectar a la base de datos."

        cur = cn.cursor()
        cur.execute("SELECT serial, clave, fecha_expiracion, hardware_id FROM licencia LIMIT 1")
        row = cur.fetchone()
        cur.close(); cn.close()

        if not row:
            return False, "Debe activar la licencia."

        serial, _, fecha_exp_enc, hw_guardado = row

        # Validar hardware
        hw_actual = obtener_hardware_id()
        if hw_guardado != hw_actual:
            return False, "La licencia no corresponde a este equipo."

        # Desencriptar y parsear fecha
        try:
            if isinstance(fecha_exp_enc, bytes):
                fecha_exp_enc = fecha_exp_enc.decode("utf-8")
            fecha_str = fernet.decrypt(fecha_exp_enc.encode()).decode()
            fecha_exp = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except Exception as e:
            return False, f"La licencia tiene un formato de fecha inválido. ({e})"

        hoy = datetime.now().date()
        if hoy > fecha_exp:
            return False, f"La licencia expiró el {fecha_exp}."

        dias = (fecha_exp - hoy).days
        if 0 <= dias <= 10:
            return True, f"La licencia vencerá el {fecha_exp}. Quedan {dias} día(s)."
        return True, f"Licencia válida hasta {fecha_exp}"

    def extender_licencia(self, nueva_fecha, serial, clave):
        # Validaciones de formato/fecha
        try:
            fecha_dt = datetime.strptime(nueva_fecha, "%Y-%m-%d").date()
        except ValueError:
            return False, "Formato de fecha inválido. Usa YYYY-MM-DD."
        if fecha_dt <= datetime.now().date():
            return False, "La nueva fecha debe ser posterior a hoy."

        cn = conectar_base_datos()
        if not cn:
            return False, "No se pudo conectar a la base de datos."

        cur = cn.cursor()
        cur.execute("SELECT hardware_id FROM licencia WHERE serial=%s", (serial,))
        row = cur.fetchone()
        if not row:
            cur.close(); cn.close()
            return False, "No existe una licencia con ese serial."

        hw_guardado = row[0]

        # Validar clave maestra
        if not bcrypt.checkpw(clave.encode(), self.CLAVE_PREDEFINIDA_HASH.encode()):
            cur.close(); cn.close()
            return False, "Clave incorrecta. No se puede extender la licencia."

        # Validar hardware
        if hw_guardado != obtener_hardware_id():
            cur.close(); cn.close()
            return False, "Esta licencia pertenece a otro equipo."

        # Encriptar nueva fecha
        fecha_enc = fernet.encrypt(nueva_fecha.encode()).decode()
        cur.execute("UPDATE licencia SET fecha_expiracion=%s WHERE serial=%s", (fecha_enc, serial))
        cn.commit()
        cur.close(); cn.close()
        return True, f"Licencia extendida hasta {nueva_fecha}"
