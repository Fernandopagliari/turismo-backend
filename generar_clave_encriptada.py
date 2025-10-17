# -*- coding: utf-8 -*-
# generar_clave_encriptada.py
import bcrypt

clave = b"Perroponce4472801"  # la clave en texto plano que querés usar
hash_generado = bcrypt.hashpw(clave, bcrypt.gensalt())
print(hash_generado.decode())

