# hardware_id.py
import uuid
import hashlib
import platform

def obtener_hardware_id():
    """
    Obtiene un identificador único del hardware del equipo.
    Actualmente se basa en la dirección MAC, pero puede extenderse
    con CPU, Disco u otros identificadores si se necesita más seguridad.
    """
    try:
        # Dirección MAC
        mac = uuid.getnode()
        mac_str = ':'.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))

        # 🔹 Info adicional para robustecer el ID (opcional)
        sistema = platform.system()
        release = platform.release()
        version = platform.version()

        raw_id = f"{mac_str}-{sistema}-{release}-{version}"

        # 🔹 Hasheamos para no guardar datos sensibles directamente
        hardware_hash = hashlib.sha256(raw_id.encode()).hexdigest()

        return hardware_hash
    except Exception as e:
        # En caso de error, devolvemos algo consistente
        return hashlib.sha256("fallback-hwid".encode()).hexdigest()
