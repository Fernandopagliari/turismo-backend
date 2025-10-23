from flask import Flask, send_from_directory
import os

app = Flask(__name__)

@app.route('/test')
def test_frontend():
    """Página simple de prueba para verificar si Flask sirve contenido"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Frontend</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f0f0f0; }
            .success { background: green; color: white; padding: 10px; }
        </style>
    </head>
    <body>
        <h1>✅ Flask Sirviendo Correctamente</h1>
        <div class="success">Backend funcionando - El problema es en el frontend Vue.js</div>
        <p>APIs probadas:</p>
        <ul>
            <li><a href="/api/health">/api/health</a></li>
            <li><a href="/api/configuracion">/api/configuracion</a></li>
            <li><a href="/api/secciones">/api/secciones</a></li>
        </ul>
        <p>Si ves esta página, Flask está sirviendo contenido HTML correctamente.</p>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(port=5001)