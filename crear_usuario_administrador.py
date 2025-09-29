# Script para insertar un usuario administrador manualmente (una sola vez)
from basededatos import conectar

conexion = conectar()
cursor = conexion.cursor()

cursor.execute("""
    INSERT INTO usuarios (
        apellido_nombres_usuario,
        dni_usuario,
        domicilio_usuario,
        cocalidad_usuario,
        provincia_usuario,
        telefono_usuario,
        email_usuario,
        nombre_usuario_acceso,
        password_usuario,
        foto_usuario,
        rol_usuario
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    "Admin Principal",
    "12345678",
    "Casa Central",
    "Ciudad",
    "Provincia",
    "123456789",
    "admin@example.com",
    "admin",         # nombre_usuario_acceso
    "admin123",      # contraseña (sin cifrar por ahora)
    "",              # ruta foto vacía
    "admin"          # rol_usuario
))

conexion.commit()
conexion.close()
print("Usuario admin creado.")
