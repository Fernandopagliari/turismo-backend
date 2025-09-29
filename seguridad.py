# src/backend/seguridad.py
import os
from cryptography.fernet import Fernet

BASE_DIR = os.path.dirname(__file__)
KEY_PATH = os.path.join(BASE_DIR, "key.key")

if not os.path.exists(KEY_PATH):
    # Seguridad: si falta, la generamos (o podés hacer que falle)
    with open(KEY_PATH, "wb") as f:
        f.write(Fernet.generate_key())

with open(KEY_PATH, "rb") as f:
    CLAVE = f.read()

fernet = Fernet(CLAVE)
