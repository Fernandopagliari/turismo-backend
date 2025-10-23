import os
import shutil

def verificar_estructura():
    print("🔍 VERIFICANDO ESTRUCTURA DE ARCHIVOS")
    print("=" * 50)
    
    # Verificar frontend
    frontend_paths = [
        "turismo-frontend",
        "frontend", 
        "."
    ]
    
    for path in frontend_paths:
        dist_path = os.path.join(path, "dist")
        if os.path.exists(dist_path):
            print(f"✅ DIST encontrada en: {dist_path}")
            archivos = os.listdir(dist_path)
            print(f"   📁 Archivos: {len(archivos)}")
            for archivo in archivos[:5]:  # Primeros 5
                print(f"     - {archivo}")
            if "index.html" in archivos:
                print("   ✅ index.html presente")
            break
    else:
        print("❌ DIST no encontrada en ninguna ubicación")
    
    # Verificar backend
    backend_paths = [
        "turismo-backend", 
        "backend",
        "."
    ]
    
    for path in backend_paths:
        if os.path.exists(path):
            dist_backend = os.path.join(path, "dist")
            if os.path.exists(dist_backend):
                print(f"✅ DIST en backend: {dist_backend}")
            else:
                print(f"❌ DIST NO en backend: {path}")
            
            # Verificar archivos clave
            api_py = os.path.join(path, "api.py")
            if os.path.exists(api_py):
                print(f"✅ api.py en: {api_py}")
            else:
                print(f"❌ api.py NO en: {path}")

if __name__ == "__main__":
    verificar_estructura()