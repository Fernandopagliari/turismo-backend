import os
import shutil
import glob

def copiar_todo_manual():
    print("📦 COPIANDO ARCHIVOS MANUALMENTE...")
    
    dist_dir = "dist"
    backend_dir = "turismo-backend"
    
    # 1. Crear estructura básica en dist
    os.makedirs(os.path.join(dist_dir, "mysql", "connector"), exist_ok=True)
    
    # 2. Copiar directorios del proyecto
    directorios_proyecto = [
        "assets",
        "interfaz", 
        "cache_imagenes",
        "dist",
        "public", 
        "react-build"
    ]
    
    for dir_name in directorios_proyecto:
        origen = os.path.join(backend_dir, dir_name)
        destino = os.path.join(dist_dir, dir_name)
        if os.path.exists(origen):
            if os.path.exists(destino):
                shutil.rmtree(destino)
            shutil.copytree(origen, destino)
            print(f"✅ Copiado: {dir_name}")
    
    # 3. Copiar archivos individuales
    archivos_individuales = [
        ".env", "config.ini", "key.key", "mysql_config.json"
    ]
    
    for archivo in archivos_individuales:
        origen = os.path.join(backend_dir, archivo)
        destino = os.path.join(dist_dir, archivo)
        if os.path.exists(origen):
            shutil.copy2(origen, destino)
            print(f"✅ Copiado: {archivo}")
    
    # 4. Copiar MySQL locales
    locales_origen = r"C:\Users\Fernando\AppData\Local\Programs\Python\Python39-32\lib\site-packages\mysql\connector\locales"
    locales_destino = os.path.join(dist_dir, "mysql", "connector", "locales")
    if os.path.exists(locales_origen):
        shutil.copytree(locales_origen, locales_destino)
        print("✅ Copiado: MySQL locales")
    
    # 5. Copiar MySQL plugins
    plugins_origen = r"C:\Users\Fernando\AppData\Local\Programs\Python\Python39-32\lib\site-packages\mysql\connector\plugins"
    plugins_destino = os.path.join(dist_dir, "mysql", "connector", "plugins")
    if os.path.exists(plugins_origen):
        shutil.copytree(plugins_origen, plugins_destino)
        print("✅ Copiado: MySQL plugins")
    
    print("🎯 COPIA MANUAL COMPLETADA")

if __name__ == "__main__":
    copiar_todo_manual()