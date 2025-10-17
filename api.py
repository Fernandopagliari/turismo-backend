# -*- coding: utf-8 -*-
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import os
from datetime import datetime

app = Flask(__name__, static_folder='../frontend/build', static_url_path='')
CORS(app)

# =========================
# CONFIGURACIÓN TEMPORAL PARA PRIMERA INSTALACIÓN
# =========================
CONFIG_TEMPORAL = {
    'local': {
        'host': 'localhost',
        'user': 'root',
        'password': 'Perroponce@4472801',
        'database': 'databaseapp', 
        'port': 3306,
        'base_url': 'http://localhost:5000'
    },
    'hosting': {
        'host': 'shinkansen.proxy.rlwy.net',
        'user': 'root',
        'password': 'modwetYgGSblbVwIoVyvOoYQMPacXSjZ',
        'database': 'railway',
        'port': 44292,
        'base_url': 'https://turismo-regional.up.railway.app'
    }
}

# =========================
# RUTAS PARA ARCHIVOS ESTÁTICOS
# =========================

@app.route("/static-assets/<path:filename>")
def servir_assets(filename):
    """Servir archivos estáticos desde la carpeta assets"""
    assets_path = os.path.join(os.path.dirname(__file__), 'assets')
    full_path = os.path.join(assets_path, filename)
    
    if not os.path.exists(full_path):
        return jsonify({"error": "Archivo no encontrado"}), 404
    
    return send_from_directory(assets_path, filename)

# =========================
# SISTEMA DE CONEXIÓN SIMPLIFICADO Y EFICIENTE
# =========================

def detectar_entorno():
    """Detecta si estamos en local o hosting"""
    if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('DATABASE_URL'):
        return 'hosting'
    return 'local'

def get_db_config():
    """Obtiene configuración - VERSIÓN SIMPLIFICADA"""
    entorno = detectar_entorno()
    print(f"🌍 Entorno: {entorno}")
    
    # ✅ PRIMERO: Intentar con configuración de tablas
    config = obtener_configuracion_desde_bd(entorno)
    
    # ✅ SEGUNDO: Si falla, usar configuración temporal
    if config.get('fuente', '').startswith('harcodeado'):
        print(f"⚠️  Usando configuración temporal para {entorno}")
        config_temp = CONFIG_TEMPORAL[entorno].copy()
        config_temp['fuente'] = f'temporal_{entorno}'
        return config_temp
    
    return config

def obtener_configuracion_desde_bd(tipo='local'):
    """
    PRIMERO intenta leer de las tablas de BD LOCAL
    """
    try:
        print(f"🔍 Buscando configuración en BD LOCAL para: {tipo}")
        
        # ✅ SIEMPRE conectar a la BD LOCAL para leer la configuración
        config_conexion_local = {
            'host': 'localhost',
            'user': 'root',
            'password': 'Perroponce@4472801',
            'database': 'databaseapp',
            'port': 3306
        }
        
        print(f"🔌 Conectando a BD LOCAL: {config_conexion_local['host']}:{config_conexion_local['port']}")
        
        # ✅ CONEXIÓN A BD LOCAL
        conn = mysql.connector.connect(**config_conexion_local)
        cursor = conn.cursor(dictionary=True)
        
        # ✅ Buscar en la tabla correspondiente según el tipo
        if tipo == 'local':
            tabla = 'datos_host_local'
        else:
            tabla = 'datos_hosting'  # Esta tabla está en tu BD LOCAL
        
        print(f"📊 Consultando tabla: {tabla}")
        
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
            print(f"   📍 Host: {config_db['host']}")
            print(f"   👤 Usuario: {config_db['usuario']}")
            print(f"   🗃️  Base: {config_db['base_datos']}")
            print(f"   🔌 Puerto: {config_db['puerto']}")
            
            config_final = {
                'host': config_db['host'],
                'user': config_db['usuario'],
                'password': config_db['password'],
                'database': config_db['base_datos'],
                'port': config_db['puerto'],
                'fuente': f'tabla_{tabla}'
            }
            
            if config_db.get('base_url'):
                config_final['base_url'] = config_db['base_url']
                
            return config_final
            
        else:
            print(f"⚠️ Tabla '{tabla}' existe pero NO tiene registros activos")
            return {'fuente': f'harcodeado_{tipo}_sin_datos'}
            
    except Exception as e:
        print(f"❌ ERROR CRÍTICO obteniendo configuración {tipo}: {str(e)}")
        print(f"   Tipo de error: {type(e).__name__}")
        return {'fuente': f'harcodeado_{tipo}_error'}
    
def conectar_bd():
    """Conexión simplificada a la BD"""
    try:
        config = get_db_config()
        
        # Conexión principal
        connection = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            port=config['port']
        )
        
        print("✅ Conexión exitosa")
        return connection
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None

# =========================
# ENDPOINTS ESENCIALES
# =========================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check simplificado"""
    conn = conectar_bd()
    estado = "conectada" if conn else "desconectada"
    
    if conn:
        conn.close()
    
    return jsonify({
        "status": "ok",
        "base_datos": estado,
        "entorno": detectar_entorno()
    })

@app.route('/api/instalar-sistema', methods=['POST'])
def instalar_sistema():
    """Endpoint para instalar el sistema completo"""
    try:
        # Configuración de Railway
        config_railway = CONFIG_TEMPORAL['hosting']
        
        conn = mysql.connector.connect(**config_railway)
        cursor = conn.cursor()
        
        # Crear tabla datos_hosting si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS datos_hosting (
                id_config INT AUTO_INCREMENT PRIMARY KEY,
                host VARCHAR(255) NOT NULL,
                usuario VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                base_datos VARCHAR(255) NOT NULL,
                puerto INT DEFAULT 3306,
                base_url VARCHAR(255),
                activo BOOLEAN DEFAULT TRUE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insertar configuración actual de Railway
        cursor.execute("""
            INSERT INTO datos_hosting 
            (host, usuario, password, base_datos, puerto, base_url, activo)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
        """, (
            config_railway['host'],
            config_railway['user'],
            config_railway['password'],
            config_railway['database'],
            config_railway['port'],
            config_railway['base_url']
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'mensaje': 'Sistema instalado correctamente',
            'tabla_creada': True,
            'configuracion_guardada': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/estado-sistema', methods=['GET'])
def estado_sistema():
    """Verificar estado del sistema"""
    try:
        config_railway = CONFIG_TEMPORAL['hosting']
        conn = mysql.connector.connect(**config_railway)
        cursor = conn.cursor(dictionary=True)
        
        # Verificar tabla datos_hosting
        cursor.execute("""
            SELECT COUNT(*) as existe
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'railway' AND TABLE_NAME = 'datos_hosting'
        """)
        tabla_existe = cursor.fetchone()['existe'] > 0
        
        resultado = {'tabla_datos_hosting_existe': tabla_existe}
        
        if tabla_existe:
            cursor.execute("SELECT COUNT(*) as count FROM datos_hosting WHERE activo = TRUE")
            resultado['registros_activos'] = cursor.fetchone()['count']
        
        conn.close()
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug-config-detallado', methods=['GET'])
def debug_config_detallado():
    """Debug detallado del proceso de configuración"""
    try:
        entorno = detectar_entorno()
        print(f"🎯 INICIANDO DEBUG - Entorno: {entorno}")
        
        # 1. Obtener configuración paso a paso
        print("📋 Paso 1: Obteniendo configuración...")
        config = obtener_configuracion_desde_bd(entorno)
        
        print(f"✅ Configuración obtenida: {config}")
        
        # 2. Mostrar qué se obtuvo
        safe_config = config.copy()
        if 'password' in safe_config:
            safe_config['password'] = '***'
        
        return jsonify({
            'estado': 'debug_completado',
            'entorno': entorno,
            'configuracion_obtenida': safe_config,
            'fuente': config.get('fuente', 'desconocida')
        })
        
    except Exception as e:
        return jsonify({
            'estado': 'error_debug',
            'error': str(e)
        }), 500

@app.route('/api/debug-config-hosting', methods=['GET'])
def debug_config_hosting():
    """Debug específico para la configuración de hosting"""
    try:
        print("🔍 DEBUG: Iniciando obtención de configuración hosting...")
        
        # 1. Primero probar conexión directa a Railway
        print("🔌 Probando conexión directa a Railway...")
        try:
            conn_direct = mysql.connector.connect(
                host='shinkansen.proxy.rlwy.net',
                user='root',
                password='modwetYgGSblbVwIoVyvOoYQMPacXSjZ',
                database='railway',
                port=44292
            )
            conn_direct.close()
            print("✅ Conexión directa a Railway: EXITOSA")
            conexion_directa = "exitosa"
        except Exception as e:
            print(f"❌ Conexión directa a Railway: FALLIDA - {e}")
            conexion_directa = f"fallida - {e}"
        
        # 2. Ahora probar obtener configuración desde BD local
        print("📊 Probando obtener configuración desde BD local...")
        config = obtener_configuracion_desde_bd('hosting')
        
        print(f"🎯 Resultado de obtener_configuracion_desde_bd(): {config}")
        
        # 3. Probar conexión con la configuración obtenida
        conexion_config = "no_se_probo"
        if config and 'host' in config:
            print("🔌 Probando conexión con configuración obtenida...")
            try:
                conn_config = mysql.connector.connect(
                    host=config['host'],
                    user=config['user'],
                    password=config['password'],
                    database=config['database'],
                    port=config['port']
                )
                conn_config.close()
                print("✅ Conexión con configuración obtenida: EXITOSA")
                conexion_config = "exitosa"
            except Exception as e:
                print(f"❌ Conexión con configuración obtenida: FALLIDA - {e}")
                conexion_config = f"fallida - {e}"
        
        return jsonify({
            'conexion_directa_railway': conexion_directa,
            'configuracion_obtenida': config,
            'conexion_con_configuracion': conexion_config,
            'estado': 'debug_completado'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =========================
# ENDPOINTS DE LA APLICACIÓN
# =========================

@app.route('/api/configuracion', methods=['GET'])
def obtener_configuracion():
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "BD no disponible"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM configuracion_app WHERE habilitar = 1 LIMIT 1")
        config = cursor.fetchone() or {}
        conn.close()
        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/secciones', methods=['GET'])
def obtener_secciones():
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "BD no disponible"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM secciones WHERE habilitar = 1 ORDER BY orden")
        secciones = cursor.fetchall()
        
        for seccion in secciones:
            cursor.execute("SELECT * FROM sub_secciones WHERE id_seccion = %s AND habilitar = 1 ORDER BY orden", (seccion['id_seccion'],))
            seccion['subsecciones'] = cursor.fetchall()
        
        conn.close()
        return jsonify(secciones)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/regiones', methods=['GET'])
def obtener_regiones():
    conn = conectar_bd()
    if not conn:
        return jsonify({"error": "BD no disponible"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM regiones_zonas WHERE habilitar = 1 ORDER BY orden")
        regiones = cursor.fetchall()
        conn.close()
        return jsonify(regiones)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# INICIALIZACIÓN
# =========================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 50)
    print("🚀 SISTEMA TURISMO - INICIANDO")
    print("=" * 50)
    
    entorno = detectar_entorno()
    print(f"🌍 Entorno: {entorno}")
    
    # Probar conexión
    conn = conectar_bd()
    if conn:
        print("✅ Conexión a BD: EXITOSA")
        conn.close()
    else:
        print("❌ Conexión a BD: FALLIDA")
    
    app.run(host='0.0.0.0', port=port, debug=(entorno == 'local'))