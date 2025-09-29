# src/backend/generar_clave_fernet.py
from cryptography.fernet import Fernet
import os

base_dir = os.path.dirname(__file__)
key_path = os.path.join(base_dir, "key.key")

if os.path.exists(key_path):
    print("Ya existe:", key_path)
else:
    with open(key_path, "wb") as f:
        f.write(Fernet.generate_key())
    print("✅ Clave creada en:", key_path)
