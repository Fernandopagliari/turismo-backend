# -*- coding: utf-8 -*-
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import os
from datetime import datetime

# ⚠️ ELIMINAR el parche de aquí - solo debe estar en database_local.py
# El parche se aplicará automáticamente cuando database_local.py lo active

app = Flask(__name__, static_folder='../frontend/build', static_url_path='')
CORS(app)

# =========================
# CONFIGURACIONES HARCODEADAS DE RESPALDO
# =========================
CONFIG_LOCAL = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Perroponce@4472801',
    'database': 'databaseapp', 
    'port': 3306,
    'base_url': 'http://localhost:5000'
}

CONFIG_HOSTING = {
    'host': 'shinkansen.proxy.rlwy.net',
    'user': 'root',
    'password': 'tu_password_railway',  # Reemplaza con tu password real
    'database': 'railway',
    'port': 44292,
    'base_url': 'https://turismo-regional.up.railway.app'
}

# =========================
# RUTAS PARA SERVIR ARCHIVOS ESTÁTICOS - NUEVO
# =========================

@app.route("/static-assets/<path:filename>")
def servir_assets(filename):
    """Servir archivos estáticos desde la carpeta assets"""
    assets_path = os.path.join(os.path.dirname(__file__), 'assets')
    print(f"📁 Sirviendo archivo estático: {filename}")
    print(f"📁 Desde carpeta: {assets_path}")
    
    # Verificar si el archivo existe
    full_path = os.path.join(assets_path, filename)
    if not os.path.exists(full_path):
        print(f"❌ Archivo no encontrado: {full_path}")
        return jsonify({"error": "Archivo no encontrado"}), 404
    
    print(f"✅ Archivo encontrado, sirviendo: {filename}")
    return send_from_directory(assets_path, filename)

@app.route('/api/test-assets')
def test_assets():
    """Endpoint para probar assets"""
    assets_path = os.path.join(os.path.dirname(__file__), 'assets')
    test_file = os.path.join(assets_path, 'imagenes/lugares/Astica2.jpg')
    
    return jsonify({
        'assets_path': assets_path,
        'test_file': test_file,
        'file_exists': os.path.exists(test_file),
        'current_directory': os.path.dirname(__file__),
        'message': 'Prueba la imagen en: http://localhost:5000/static-assets/imagenes/lugares/Astica2.jpg'
    })

# =========================
# FUNCIONES DE CONEXIÓN A BD (igual que antes)
# =========================

def obtener_configuracion_desde_bd(tipo='local'):
    """
    PRIMERO intenta leer de las tablas de BD
    SI FALLA → usa configuraciones harcodeadas
    """
    try:
        print(f"🔍 Buscando configuración en tabla BD para: {tipo}")
        
        # ✅ CONFIGURACIÓN PARA CONECTAR A LA BD DE CONFIGURACIÓN
        if tipo == 'local':
            config_conexion = {
                'host': CONFIG_LOCAL['host'],
                'user': CONFIG_LOCAL['user'],
                'password': CONFIG_LOCAL['password'],
                'database': CONFIG_LOCAL['database'],
                'port': CONFIG_LOCAL['port']
            }
        else:
            config_conexion = {
                'host': CONFIG_HOSTING['host'],
                'user': CONFIG_HOSTING['user'],
                'password': CONFIG_HOSTING['password'],
                'database': CONFIG_HOSTING['database'],
                'port': CONFIG_HOSTING['port']
            }
        
        # ✅ CONEXIÓN DIRECTA - sin parche forzado
        conn = mysql.connector.connect(**config_conexion)
        cursor = conn.cursor(dictionary=True)
        
        # ✅ Buscar en la tabla correspondiente
        if tipo == 'local':
            tabla = 'datos_host_local'
        else:
            tabla = 'datos_hosting'
        
        cursor.execute(f"""
            SELECT host, usuario, password, base_datos, puerto, base_url
            FROM {tabla} 
            WHERE activo = TRUE 
            ORDER BY fecha_creacion DESC 
            LIMIT 1
        """)
        
        config_db = cursor.fetchone()
        conn.close()
        
        if config_db:
            print(f"✅ Configuración encontrada en tabla '{tabla}'")
            
            # ✅ CORREGIDO: Retornar solo los parámetros necesarios para conexión
            config_final = {
                'host': config_db['host'],
                'user': config_db['usuario'],
                'password': config_db['password'],
                'database': config_db['base_datos'],
                'port': config_db['puerto'],
                'fuente': f'tabla_{tabla}'
            }
            
            # ✅ Agregar base_url como metadata separada (no para conexión)
            if config_db.get('base_url'):
                config_final['base_url'] = config_db['base_url']
                
            return config_final
            
        else:
            print(f"⚠️ Tabla '{tabla}' existe pero NO tiene registros activos")
            return obtener_config_harcodeada(tipo, 'sin_datos')
            
    except Exception as e:
        print(f"❌ Error obteniendo configuración {tipo}: {e}")
        return obtener_config_harcodeada(tipo, 'error_conexion')

def obtener_config_harcodeada(tipo, motivo):
    """Obtener configuración harcodeada - CORREGIDO"""
    if tipo == 'local':
        config = {
            'host': CONFIG_LOCAL['host'],
            'user': CONFIG_LOCAL['user'],
            'password': CONFIG_LOCAL['password'],
            'database': CONFIG_LOCAL['database'],
            'port': CONFIG_LOCAL['port'],
            'base_url': 'http://localhost:5000',
            'fuente': f'harcodeado_local_{motivo}'
        }
    else:
        config = {
            'host': CONFIG_HOSTING['host'],
            'user': CONFIG_HOSTING['user'],
            'password': CONFIG_HOSTING['password'],
            'database': CONFIG_HOSTING['database'],
            'port': CONFIG_HOSTING['port'],
            'base_url': 'https://turismo-regional.up.railway.app',
            'fuente': f'harcodeado_hosting_{motivo}'
        }
    
    print(f"   Usando configuración harcodeada para {tipo} ({motivo})")
    return config

def detectar_entorno():
    """Detecta automáticamente si estamos en local o producción"""
    if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('DATABASE_URL'):
        return 'hosting'
    elif os.environ.get('RENDER'):
        return 'hosting'
    else:
        return 'local'

def get_db_config():
    """Obtiene la configuración con sistema de fallback inteligente"""
    entorno = detectar_entorno()
    print(f"🌍 Entorno detectado: {entorno}")
    
    # Obtener configuración (primero de BD, luego harcodeada)
    config = obtener_configuracion_desde_bd(entorno)
    
    print(f"📊 Fuente de configuración: {config.get('fuente', 'desconocida')}")
    return config

def conectar_bd():
    """Conexión con múltiples niveles de fallback"""
    try:
        config = get_db_config()
        
        # Log seguro
        safe_config = {k: v for k, v in config.items() if k != 'password'}
        safe_config['password'] = '***'
        print(f"🔌 Intentando conexión con: {safe_config}")
        
        # Conexión principal
        connection_config = {
            'host': config['host'],
            'user': config['user'],
            'password': config['password'],
            'database': config['database'],
            'port': config['port']
        }
        
        # ✅ CONEXIÓN DIRECTA - sin parche forzado
        connection = mysql.connector.connect(**connection_config)
        print("✅ Conexión a BD exitosa")
        return connection
        
    except Exception as e:
        print(f"❌ Error en conexión principal: {str(e)}")
        
        # ✅ FALLBACK: Intentar con configuración local directa
        print("🔄 Intentando fallback a conexión local...")
        try:
            # ✅ CONEXIÓN DIRECTA - sin parche forzado
            connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password='Perroponce@4472801',
                database='databaseapp',
                port=3306
            )
            print("✅ Conexión de fallback exitosa")
            return connection
        except Exception as fallback_error:
            print(f"❌ Fallback también falló: {fallback_error}")
            return None

# =========================
# ENDPOINTS DE DIAGNÓSTICO
# =========================
@app.route('/api/debug/config', methods=['GET'])
def debug_config():
    """Endpoint para debug de configuración"""
    entorno = detectar_entorno()
    config = get_db_config()
    
    # Info segura para mostrar
    safe_config = config.copy()
    if 'password' in safe_config:
        safe_config['password'] = '***'
    
    # Probar conexión
    conn = conectar_bd()
    estado_conexion = "conectada" if conn else "desconectada"
    if conn:
        conn.close()
    
    return jsonify({
        'entorno': entorno,
        'configuracion': safe_config,
        'estado_conexion': estado_conexion,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/debug/tablas', methods=['GET'])
def debug_tablas():
    """Verificar existencia de tablas de configuración - COMPLETAMENTE CORREGIDO"""
    try:
        # Configuración de conexión corregida
        config_conexion = {
            'host': CONFIG_LOCAL['host'],
            'user': CONFIG_LOCAL['user'],
            'password': CONFIG_LOCAL['password'],
            'database': CONFIG_LOCAL['database'],
            'port': CONFIG_LOCAL['port']
        }
        
        # ✅ CONEXIÓN DIRECTA - sin parche forzado
        conn = mysql.connector.connect(**config_conexion)
        cursor = conn.cursor()
        
        tablas = ['datos_host_local', 'datos_hosting']
        resultado = {}
        
        for tabla in tablas:
            try:
                # ✅ CORREGIDO: Verificar si la tabla existe usando INFORMATION_SCHEMA
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """, (CONFIG_LOCAL['database'], tabla))
                
                tabla_existe = cursor.fetchone()[0] > 0
                
                if tabla_existe:
                    # ✅ CORREGIDO: Contar registros activos con cursor nuevo
                    cursor2 = conn.cursor()
                    cursor2.execute(f"SELECT COUNT(*) as count FROM {tabla} WHERE activo = TRUE")
                    count = cursor2.fetchone()[0]
                    cursor2.close()
                    
                    resultado[tabla] = {'existe': True, 'registros_activos': count}
                else:
                    resultado[tabla] = {'existe': False, 'registros_activos': 0}
                    
            except mysql.connector.Error as e:
                # Si hay error, asumimos que la tabla no existe o hay problema
                resultado[tabla] = {'existe': False, 'registros_activos': 0, 'error': str(e)}
        
        cursor.close()
        conn.close()
        return jsonify({'tablas': resultado})
        
    except Exception as e:
        return jsonify({'error': f'No se pudo verificar tablas: {str(e)}'}), 500

# =========================
# ENDPOINTS PRINCIPALES
# =========================
@app.route('/api/health', methods=['GET'])
def health_check():
    config = get_db_config()
    entorno = detectar_entorno()
    
    conn = conectar_bd()
    bd_status = "conectada" if conn else "desconectada"
    if conn:
        conn.close()
    
    return jsonify({
        "status": "ok",
        "entorno": entorno,
        "base_datos": bd_status,
        "fuente_configuracion": config.get('fuente', 'desconocida'),
        "configuracion": {
            "host": config['host'],
            "base_datos": config['database'],
            "puerto": config['port']
        }
    })

@app.route('/api/info-conexion', methods=['GET'])
def info_conexion():
    """Información detallada de la conexión (sin passwords)"""
    config = get_db_config()
    entorno = detectar_entorno()
    
    # Info segura (sin password)
    info_segura = {
        'entorno': entorno,
        'host': config['host'],
        'usuario': config['user'],
        'base_datos': config['database'],
        'puerto': config['port'],
        'base_url': config.get('base_url', 'No configurada')
    }
    
    return jsonify(info_segura)

@app.route('/api/configuracion', methods=['GET'])
def obtener_configuracion():
    """Obtener configuración de la aplicación"""
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                id_config, titulo_app, logo_app_ruta_relativa,
                icono_hamburguesa_ruta_relativa,
                icono_cerrar_ruta_relativa,
                hero_titulo, hero_imagen_ruta_relativa,
                footer_texto, direccion_facebook, direccion_instagram,
                direccion_twitter, direccion_youtube, correo_electronico, habilitar
            FROM configuracion_app 
            WHERE habilitar = 1 
            LIMIT 1
        """)
        
        config = cursor.fetchone()
        conn.close()
        
        if config:
            return jsonify(config)
        else:
            return jsonify({})
            
    except Exception as e:
        print(f"❌ Error en configuración: {str(e)}")
        return jsonify({"error": f"Error del servidor: {str(e)}"}), 500

@app.route('/api/secciones', methods=['GET'])
def obtener_secciones():
    """Obtener secciones con sus subsecciones"""
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                id_seccion, nombre_seccion, icono_seccion, habilitar, orden
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
                    imagen_ruta_relativa, icono_ruta_relativa, itinerario_maps,
                    habilitar, fecha_desactivacion, orden, destacado,
                    foto1_ruta_relativa, foto2_ruta_relativa, 
                    foto3_ruta_relativa, foto4_ruta_relativa
                FROM sub_secciones 
                WHERE id_seccion = %s AND habilitar = 1 
                ORDER BY orden
            """, (seccion['id_seccion'],))
            
            subsecciones = cursor.fetchall()
            seccion['subsecciones'] = subsecciones
        
        conn.close()
        return jsonify(secciones)
        
    except Exception as e:
        print(f"❌ Error en secciones: {str(e)}")
        return jsonify({"error": f"Error del servidor: {str(e)}"}), 500

@app.route('/api/regiones', methods=['GET'])
def obtener_regiones():
    """Obtener todas las regiones/zonas habilitadas"""
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                id_region_zona, nombre_region_zona, 
                imagen_region_zona_ruta_relativa, habilitar, orden
            FROM regiones_zonas 
            WHERE habilitar = 1 
            ORDER BY orden ASC
        """)
        
        regiones = cursor.fetchall()
        conn.close()
        
        print(f"✅ {len(regiones)} regiones encontradas")
        return jsonify(regiones)
        
    except Exception as e:
        print(f"❌ Error en regiones: {str(e)}")
        return jsonify({"error": f"Error del servidor: {str(e)}"}), 500

# =========================
# INICIALIZACIÓN MEJORADA
# =========================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print("🚀 API UNIVERSAL - SISTEMA DE FALLBACK INTELIGENTE")
    print("=" * 60)
    
    # Mostrar información de configuración
    entorno = detectar_entorno()
    config = get_db_config()
    
    print(f"🌍 Entorno detectado: {entorno}")
    print(f"📊 Fuente de configuración: {config.get('fuente', 'desconocida')}")
    print(f"🔌 Host: {config['host']}:{config['port']}")
    print(f"🗃️ Base de datos: {config['database']}")
    print(f"👤 Usuario: {config['user']}")
    print("=" * 60)
    
    # Probar conexión
    print("🔌 Probando conexión...")
    conn = conectar_bd()
    if conn:
        conn.close()
        print("✅ Sistema de conexión verificado")
    else:
        print("❌ Sistema de conexión falló")
        print("💡 Sugerencia: Verifica que MySQL esté ejecutándose")
    
    # Iniciar servidor
    debug_mode = (entorno == 'local')
    app.run(host='0.0.0.0', port=port, debug=debug_mode)