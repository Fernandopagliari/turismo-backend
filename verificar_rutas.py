import mysql.connector
import os

mysql_path = os.path.dirname(mysql.connector.__file__)
locales_path = os.path.join(mysql_path, 'locales')
plugins_path = os.path.join(mysql_path, 'plugins')

print(f"🔍 Ruta MySQL: {mysql_path}")
print(f"🔍 Ruta locales: {locales_path}")
print(f"🔍 Ruta plugins: {plugins_path}")

# Verificar si existen
print(f"✅ Locales existe: {os.path.exists(locales_path)}")
print(f"✅ Plugins existe: {os.path.exists(plugins_path)}")

# Listar archivos en plugins
if os.path.exists(plugins_path):
    print("📁 Archivos en plugins:")
    for file in os.listdir(plugins_path):
        if file.endswith('.py'):
            print(f"   - {file}")