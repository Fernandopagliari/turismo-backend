import os
from PIL import Image

# =============================
# CONFIGURACIÓN
# =============================
BASE_PATH = "/assets/imagenes/"
EXT_VALIDAS = (".jpg", ".jpeg", ".png", ".bmp")
MAX_SIZE = (1600, 1600)
QUALITY = 75


def convertir_imagen(ruta_original):
    ruta_webp = os.path.splitext(ruta_original)[0] + ".webp"

    # Si ya existe WebP, no reconvertimos
    if os.path.exists(ruta_webp):
        return

    with Image.open(ruta_original) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.thumbnail(MAX_SIZE)
        img.save(ruta_webp, "WEBP", quality=QUALITY, method=6)

    print(f"✔ {ruta_original} → {ruta_webp}")


def recorrer_y_convertir():
    for root, _, files in os.walk(BASE_PATH):
        for file in files:
            if file.lower().endswith(EXT_VALIDAS):
                ruta = os.path.join(root, file)
                try:
                    convertir_imagen(ruta)
                except Exception as e:
                    print(f"❌ Error en {ruta}: {e}")


if __name__ == "__main__":
    print("🚀 Iniciando conversión a WebP...")
    recorrer_y_convertir()
    print("✅ Conversión finalizada")

