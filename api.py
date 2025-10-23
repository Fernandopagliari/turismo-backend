# -*- coding: utf-8 -*-
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import os
from datetime import datetime

app = Flask(__name__, static_folder='dist', static_url_path='')
CORS(app)

# =========================
# CONFIGURACIÓN MEJORADA - BD LOCAL Y REMOTA
# =========================

def detectar_entorno():
    """Detecta si estamos en local o hosting"""
    if os.environ.get('MYSQLHOST') or os.environ.get('RAILWAY_ENVIRONMENT'):
        return 'hosting'
    return 'local'

def conectar_a_bd_local():
    """✅ CONEXIÓN SIMPLIFICADA a BD LOCAL usando variables de entorno"""
    try:
        conn = mysql.connector.connect(
            host=os.environ.get('LOCAL_DB_HOST', 'localhost'),
            user=os.environ.get('LOCAL_DB_USER', 'root'),
            password=os.environ.get('LOCAL_DB_PASSWORD', ''),
            database=os.environ.get('LOCAL_DB_NAME', 'databaseapp'),
            port=int(os.environ.get('LOCAL_DB_PORT', 3306))
        )
        return conn
    except Exception as e:
        print(f"❌ Error conectando a BD local: {e}")
        return None

def conectar_a_bd_remota():
    """✅ CONEXIÓN DIRECTA a BD REMOTA usando variables de RENDER"""
    try:
        conn = mysql.connector.connect(
            host=os.environ.get('MYSQLHOST'),
            user=os.environ.get('MYSQLUSER'),
            password=os.environ.get('MYSQLPASSWORD'),
            database=os.environ.get('MYSQLDATABASE'),
            port=int(os.environ.get('MYSQLPORT', 3306))
        )
        return conn
    except Exception as e:
        print(f"❌ Error conectando a BD remota: {e}")
        return None

def obtener_config_desde_tabla(tabla):
    """✅ Obtiene configuración ACTIVA desde tabla específica (local o remota)"""
    try:
        if detectar_entorno() == 'local':
            # ✅ Local: leer de BD local
            conn = conectar_a_bd_local()
            fuente = 'local'
        else:
            # ✅ Hosting: leer de BD remota
            conn = conectar_a_bd_remota()
            fuente = 'remota'
        
        if not conn:
            raise Exception("No se pudo conectar a BD")
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(f"""
            SELECT host, usuario, password, base_datos, puerto, base_url
            FROM {tabla} 
            WHERE activo = 1 
            ORDER BY fecha_creacion DESC 
            LIMIT 1
        """)
        
        config = cursor.fetchone()
        conn.close()
        
        if not config:
            raise Exception(f"No hay registros ACTIVOS en {tabla} ({fuente})")
        
        return {
            'host': config['host'],
            'user': config['usuario'], 
            'password': config['password'],
            'database': config['base_datos'],
            'port': config['puerto'],
            'base_url': config.get('base_url', ''),
            'fuente': f'tabla_{tabla}_{fuente}'
        }
        
    except Exception as e:
        print(f"❌ Error leyendo {tabla}: {e}")
        raise e

def get_db_config():
    """✅ Obtiene configuración desde tablas (local o remota)"""
    entorno = detectar_entorno()
    print(f"🌍 Entorno detectado: {entorno}")
    
    try:
        if entorno == 'local':
            # ✅ Usar datos_host_local (activo=1) desde BD local
            config = obtener_config_desde_tabla('datos_host_local')
            print(f"📍 Config local: {config['host']}:{config['port']}")
        else:
            # ✅ Usar datos_hosting (activo=1) desde BD remota
            config = obtener_config_desde_tabla('datos_hosting')
            print(f"📍 Config hosting: {config['host']}:{config['port']}")
        
        return config
        
    except Exception as e:
        print(f"❌ Error crítico obteniendo configuración: {e}")
        # ✅ FALLBACK: Conexión directa con variables de entorno
        print("🔄 Usando conexión directa con variables de entorno...")
        if entorno == 'hosting':
            return {
                'host': os.environ.get('MYSQLHOST'),
                'user': os.environ.get('MYSQLUSER'),
                'password': os.environ.get('MYSQLPASSWORD'),
                'database': os.environ.get('MYSQLDATABASE'),
                'port': int(os.environ.get('MYSQLPORT', 3306)),
                'fuente': 'variables_entorno_directo'
            }
        else:
            raise e

def conectar_bd():
    """✅ Conexión usando configuración de las tablas CON FALLBACK"""
    try:
        config = get_db_config()
        
        print(f"🔌 Conectando a: {config['host']}:{config['port']}")
        
        conn = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            port=config['port']
        )
        
        print(f"✅ Conexión exitosa a: {config['database']}")
        return conn
        
    except Exception as e:
        print(f"❌ Error de conexión con configuración: {e}")
        
        # ✅ FALLBACK DIRECTA
        print("🔄 Intentando conexión directa...")
        if detectar_entorno() == 'hosting':
            return conectar_a_bd_remota()
        else:
            return conectar_a_bd_local()

# =========================
# SERVIR FRONTEND DESDE CARPETA DIST - CON DIAGNÓSTICO
# =========================

@app.route('/')
def serve_frontend():
    """Servir el frontend Vue.js con diagnóstico integrado"""
    try:
        # ✅ DIAGNÓSTICO: Verificar que dist/ existe
        if not os.path.exists('dist'):
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error - No dist/</title>
                <style>
                    body { font-family: Arial; margin: 40px; background: #ffebee; color: #c62828; }
                    .error-box { background: #ffcdd2; padding: 20px; border-radius: 5px; margin: 20px 0; }
                </style>
            </head>
            <body>
                <h1>❌ ERROR: No existe carpeta dist/</h1>
                <div class="error-box">
                    <p><strong>Problema:</strong> El frontend no fue construido o no se copió al backend.</p>
                    <p><strong>Solución:</strong> Ejecuta <code>npm run build</code> en el frontend y copia la carpeta dist/ al backend.</p>
                </div>
                <p>Archivos en directorio actual:</p>
                <pre>{}</pre>
            </body>
            </html>
            """.format(os.listdir('.')), 500
        
        # ✅ DIAGNÓSTICO: Verificar index.html
        index_path = os.path.join('dist', 'index.html')
        if not os.path.exists(index_path):
            archivos_dist = os.listdir('dist')
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error - No index.html</title>
                <style>
                    body { font-family: Arial; margin: 40px; background: #fff3cd; color: #856404; }
                    .warning-box { background: #fff3cd; padding: 20px; border-radius: 5px; margin: 20px 0; }
                </style>
            </head>
            <body>
                <h1>⚠️ ERROR: index.html no encontrado en dist/</h1>
                <div class="warning-box">
                    <p><strong>Contenido de dist/:</strong> {archivos_dist}</p>
                    <p>El build de React no generó index.html correctamente.</p>
                </div>
            </body>
            </html>
            """, 500
        
        # ✅ DIAGNÓSTICO: Verificar assets/
        assets_path = os.path.join('dist', 'assets')
        if not os.path.exists(assets_path):
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error - No assets/</title>
                <style>
                    body { font-family: Arial; margin: 40px; background: #e3f2fd; color: #1565c0; }
                    .info-box { background: #e3f2fd; padding: 20px; border-radius: 5px; margin: 20px 0; }
                </style>
            </head>
            <body>
                <h1>ℹ️ ADVERTENCIA: No existe carpeta assets/</h1>
                <div class="info-box">
                    <p>La carpeta assets/ no se encontró en dist/. Esto puede causar problemas de CSS/JS.</p>
                    <p>Contenido de dist/: {}</p>
                </div>
                <p>Intentando servir el frontend de todas formas...</p>
            </body>
            </html>
            """.format(os.listdir('dist')), 200
        
        # ✅ TODO BIEN: Servir el frontend normal
        print("✅ Sirviendo frontend desde dist/index.html")
        return send_from_directory('dist', 'index.html')
        
    except Exception as e:
        # ✅ ERROR CRÍTICO: Mostrar detalles completos
        import traceback
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error Crítico</title>
            <style>
                body {{ font-family: Arial; margin: 40px; background: #f8d7da; color: #721c24; }}
                .error {{ background: #f5c6cb; padding: 20px; border-radius: 5px; margin: 10px 0; }}
                .debug {{ background: #e2e3e5; padding: 15px; margin: 10px 0; font-family: monospace; font-size: 12px; }}
            </style>
        </head>
        <body>
            <h1>🚨 ERROR CRÍTICO Sirviendo Frontend</h1>
            
            <div class="error">
                <h3>❌ Exception:</h3>
                <pre>{str(e)}</pre>
            </div>
            
            <div class="debug">
                <h3>🔍 Debug Info:</h3>
                <pre>Directorio actual: {os.getcwd()}</pre>
                <pre>Existe dist/: {os.path.exists('dist')}</pre>
                <pre>Contenido actual: {os.listdir('.')}</pre>
                <pre>Traceback: {traceback.format_exc()}</pre>
            </div>
            
            <div class="debug">
                <h3>🔗 URLs de prueba:</h3>
                <ul>
                    <li><a href="/api/health">/api/health</a> - Health check</li>
                    <li><a href="/api/debug">/api/debug</a> - Debug info</li>
                    <li><a href="/assets/index-3zJ84eex.js">Archivo JS</a> - Verificar assets</li>
                    <li><a href="/assets/index-DET4filr.css">Archivo CSS</a> - Verificar CSS</li>
                </ul>
            </div>
        </body>
        </html>
        """, 500

@app.route('/<path:path>')
def serve_static_files(path):
    """Servir archivos estáticos del frontend con diagnóstico"""
    try:
        response = send_from_directory('dist', path)
        print(f"✅ Sirviendo archivo estático: {path}")
        return response
    except Exception as e:
        print(f"❌ Error sirviendo {path}: {e}")
        return jsonify({
            "error": "Archivo no encontrado",
            "path": path,
            "available_files": os.listdir('dist') if os.path.exists('dist') else [],
            "details": str(e)
        }), 404

# =========================
# ENDPOINTS DE DIAGNÓSTICO (BAJO /api/)
# =========================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check MEJORADO con fallback"""
    try:
        conn = conectar_bd()
        estado = "conectada" if conn else "desconectada"
        
        if conn:
            # Probar que realmente funciona
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
        
        return jsonify({
            "status": "ok",
            "base_datos": estado,
            "entorno": detectar_entorno(),
            "mysql_host": os.environ.get('MYSQLHOST', 'no configurado')
        })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "base_datos": "desconectada",
            "error": str(e),
            "entorno": detectar_entorno()
        }), 500

@app.route('/api/debug', methods=['GET'])
def debug_info():
    """Endpoint de diagnóstico completo"""
    try:
        import sys
        
        files = {}
        if os.path.exists('dist'):
            files['dist'] = os.listdir('dist')
            if os.path.exists('dist/index.html'):
                files['index_size'] = os.path.getsize('dist/index.html')
        
        return jsonify({
            'status': 'running',
            'python_version': sys.version,
            'current_directory': os.getcwd(),
            'files_in_root': os.listdir('.'),
            'static_folder': app.static_folder,
            'has_dist_folder': os.path.exists('dist'),
            'files': files,
            'environment': {
                'MYSQLHOST': bool(os.environ.get('MYSQLHOST')),
                'MYSQLDATABASE': bool(os.environ.get('MYSQLDATABASE')),
                'PORT': os.environ.get('PORT')
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/info', methods=['GET'])
def api_info():
    """Información general de la API"""
    return jsonify({
        "message": "Turismo Regional API", 
        "version": "1.0",
        "frontend": "Vue.js",
        "backend": "Flask",
        "database": "MySQL",
        "status": "online"
    })

# =========================
# ENDPOINTS PRINCIPALES DE LA APLICACIÓN
# =========================

@app.route('/api/config/frontend', methods=['GET'])
def config_frontend():
    """✅ Devuelve configuración para frontend desde BD CORRECTA"""
    try:
        if detectar_entorno() == 'local':
            # ✅ Local: leer de datos_hosting en BD local
            config = obtener_config_desde_tabla('datos_hosting')
        else:
            # ✅ Hosting: leer de datos_hosting en BD remota
            config = obtener_config_desde_tabla('datos_hosting')
        
        return jsonify({
            'api_base_url': config['base_url'],
            'entorno': detectar_entorno(),
            'status': 'ok',
            'fuente': config['fuente']
        })
        
    except Exception as e:
        return jsonify({
            'api_base_url': '',
            'entorno': 'local',
            'status': 'error',
            'message': 'No se pudo obtener configuración'
        })

@app.route('/api/configuracion', methods=['GET'])
def obtener_configuracion():
    """✅ SOLO rutas relativas - basado en tu estructura real"""
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "BD no disponible"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                id_config, titulo_app, 
                logo_app_ruta_relativa,
                icono_hamburguesa_ruta_relativa,
                icono_cerrar_ruta_relativa,
                hero_titulo, 
                hero_imagen_ruta_relativa,
                footer_texto, direccion_facebook, direccion_instagram,
                direccion_twitter, direccion_youtube, correo_electronico, habilitar
            FROM configuracion_app 
            WHERE habilitar = 1 
            LIMIT 1
        """)
        config = cursor.fetchone() or {}
        conn.close()
        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/secciones', methods=['GET'])
def obtener_secciones():
    """✅ SOLO rutas relativas - basado en tu estructura real"""
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "BD no disponible"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                id_seccion, nombre_seccion, 
                icono_seccion,  -- ✅ Este campo ya es relativo en tu BD
                habilitar, orden
            FROM secciones 
            WHERE habilitar = 1 
            ORDER BY orden
        """)
        secciones = cursor.fetchall()
        
        for seccion in secciones:
            cursor.execute("""
                SELECT 
                    id_sub_seccion, id_seccion, id_region_zona, nombre_sub_seccion,
                    domicilio, latitud, longitud, distancia, numero_telefono,
                    imagen_ruta_relativa, 
                    icono_ruta_relativa, 
                    itinerario_maps,
                    habilitar, fecha_desactivacion, orden, destacado,
                    foto1_ruta_relativa, 
                    foto2_ruta_relativa, 
                    foto3_ruta_relativa, 
                    foto4_ruta_relativa
                FROM sub_secciones 
                WHERE id_seccion = %s AND habilitar = 1 
                ORDER BY orden
            """, (seccion['id_seccion'],))
            
            subsecciones = cursor.fetchall()
            seccion['subsecciones'] = subsecciones
        
        conn.close()
        return jsonify(secciones)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/regiones', methods=['GET'])
def obtener_regiones():
    """✅ SOLO rutas relativas - basado en tu estructura real"""
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "BD no disponible"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                id_region_zona, nombre_region_zona, 
                imagen_region_zona_ruta_relativa,
                habilitar, orden
            FROM regiones_zonas 
            WHERE habilitar = 1 
            ORDER BY orden
        """)
        regiones = cursor.fetchall()
        conn.close()
        return jsonify(regiones)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# ENDPOINTS DE DIAGNÓSTICO DE ASSETS (TEMPORALES)
# =========================

@app.route('/api/debug-assets')
def debug_assets():
    """✅ Ruta temporal para debuggear estructura de assets"""
    import os
    assets_path = os.path.join(os.path.dirname(__file__), 'assets')
    
    if not os.path.exists(assets_path):
        return jsonify({"error": "No existe carpeta assets", "path": assets_path})
    
    estructura = {}
    for root, dirs, files in os.walk(assets_path):
        nivel = root.replace(assets_path, '').lstrip('/')
        if nivel:
            estructura[nivel] = files[:10]  # Primeros 10 archivos
    
    return jsonify({
        "assets_path": assets_path,
        "existe": os.path.exists(assets_path),
        "estructura": estructura,
        "contenido_raiz": os.listdir(assets_path) if os.path.exists(assets_path) else []
    })
    
@app.route('/api/debug-images')
def debug_images():
    """✅ Verificar imágenes específicas"""
    import os
    base_path = os.path.join(os.path.dirname(__file__), 'assets')
    
    imagenes = {
        "icono": os.path.join(base_path, 'imagenes', 'iconos', 'valle_fertil_turismo_regional.jpg'),
        "hero": os.path.join(base_path, 'imagenes', 'portadas', 'hongo_ischigualasto.jpg')
    }
    
    resultados = {}
    for nombre, ruta in imagenes.items():
        resultados[nombre] = {
            "ruta": ruta,
            "existe": os.path.exists(ruta),
            "tamaño": os.path.getsize(ruta) if os.path.exists(ruta) else 0
        }
    
    return jsonify(resultados)

# =========================
# INICIALIZACIÓN
# =========================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 50)
    print("🚀 SISTEMA - CONEXIÓN DUAL CON FALLBACK")
    print("=" * 50)
    
    entorno = detectar_entorno()
    print(f"🌍 Entorno: {entorno}")
    
    try:
        # Probar que puede leer la configuración
        config = get_db_config()
        print(f"📊 Configuración obtenida de: {config['fuente']}")
        print(f"🔌 Host: {config['host']}:{config['port']}")
        print(f"🗃️ Base de datos: {config['database']}")
        
        # Probar conexión real
        conn = conectar_bd()
        if conn:
            print("✅ Conexión a BD: EXITOSA")
            conn.close()
        else:
            print("❌ Conexión a BD: FALLIDA")
            
    except Exception as e:
        print(f"❌ Error crítico: {e}")
    
    app.run(host='0.0.0.0', port=port, debug=(entorno == 'local'))