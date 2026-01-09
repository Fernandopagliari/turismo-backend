# utils/image_utils.py
# =========================
# UTILIDADES DE IMÁGENES
# =========================

import os

# Extensiones de imagen permitidas
EXTENSIONES_IMAGEN = (
    ".jpg", ".jpeg", ".png", ".webp",
    ".bmp", ".gif", ".svg"
)


def es_imagen_valida(nombre_archivo: str) -> bool:
    """
    Verifica si el archivo tiene una extensión de imagen válida.
    SOLO valida por extensión.
    """
    if not nombre_archivo:
        return False

    _, extension = os.path.splitext(nombre_archivo.lower())
    return extension in EXTENSIONES_IMAGEN


def normalizar_ruta_imagen(ruta: str) -> str:
    """
    Normaliza la ruta de la imagen para uso web:
    - Convierte \\ en /
    - Elimina rutas locales (C:\\fakepath)
    """
    if not ruta:
        return ""

    # Eliminar fakepath de input file
    ruta = os.path.basename(ruta)

    # Normalizar separadores
    ruta = ruta.replace("\\", "/")

    return ruta


def procesar_imagen(ruta_archivo: str) -> str:
    """
    Procesamiento NEUTRO de imágenes.

    ✔ No convierte formatos
    ✔ No genera archivos
    ✔ No elimina archivos
    ✔ Acepta JPG, PNG, WEBP, etc
    ✔ Devuelve una ruta limpia y válida

    El FRONTEND es responsable del build y optimización.
    """

    if not ruta_archivo:
        return ""

    ruta_limpia = normalizar_ruta_imagen(ruta_archivo)

    if not es_imagen_valida(ruta_limpia):
        raise ValueError(
            "Formato de imagen no soportado.\n\n"
            "Formatos permitidos:\n"
            "JPG, JPEG, PNG, WEBP, BMP, GIF, SVG"
        )

    return ruta_limpia
