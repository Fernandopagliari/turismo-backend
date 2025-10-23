import os

def verificar_estructura_clara():
    print("🎯 VERIFICACIÓN CLARA - ESTADO DEL DEPLOY")
    print("=" * 50)
    
    # Verificar frontend
    frontend_dist = "turismo-frontend/dist"
    if os.path.exists(frontend_dist):
        print("✅ FRONTEND: dist/ construida correctamente")
        archivos = os.listdir(frontend_dist)
        print(f"   📁 Contenido: {len(archivos)} elementos")
    else:
        print("❌ FRONTEND: No tiene dist/")
        return False
    
    # Verificar backend
    backend_dist = "turismo-backend/dist" 
    if os.path.exists(backend_dist):
        print("✅ BACKEND: dist/ copiada correctamente")
        archivos_backend = os.listdir(backend_dist)
        print(f"   📁 Contenido: {len(archivos_backend)} elementos")
        
        # Verificar archivos críticos
        index_path = os.path.join(backend_dist, "index.html")
        assets_path = os.path.join(backend_dist, "assets")
        
        if os.path.exists(index_path):
            print("   ✅ index.html presente")
        else:
            print("   ❌ index.html FALTANTE")
            
        if os.path.exists(assets_path):
            num_assets = len(os.listdir(assets_path))
            print(f"   ✅ assets/ presente ({num_assets} archivos)")
        else:
            print("   ❌ assets/ FALTANTE")
            
        return True
    else:
        print("❌ BACKEND: NO tiene dist/ - No copiada")
        return False

def verificar_para_deploy():
    print("\n" + "=" * 50)
    print("🚀 ESTADO PARA DEPLOY:")
    
    backend_dist = "turismo-backend/dist"
    api_py = "turismo-backend/api.py"
    
    if os.path.exists(backend_dist) and os.path.exists(api_py):
        print("🎉 ✅ LISTO PARA DEPLOY!")
        print("   • dist/ presente en backend ✓")
        print("   • api.py presente ✓")
        print("\n📝 Próximos pasos:")
        print("   1. Ejecuta backend_deploy.py")
        print("   2. O manualmente: git add, commit, push")
        print("   3. Render detectará los cambios automáticamente")
    else:
        print("❌ NO LISTO - Faltan archivos")
        if not os.path.exists(backend_dist):
            print("   • dist/ no encontrada en backend")
        if not os.path.exists(api_py):
            print("   • api.py no encontrado")

if __name__ == "__main__":
    verificar_estructura_clara()
    verificar_para_deploy()