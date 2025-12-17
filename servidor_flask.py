"""
SERVIDOR FLASK - SISTEMA DE DETECCIÓN DE FUGAS
Versión Final para PythonAnywhere
"""

from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
import json
import os
import time

app = Flask(__name__)

# Almacenamiento de paquetes (máximo 60 por tarjeta)
paquetes_tarjeta1 = []
paquetes_tarjeta2 = []
MAX_PAQUETES = 60

# Archivo para persistir datos
ARCHIVO_DATOS = 'paquetes_sensores.json'

# Variable para análisis de Raspberry Pi
resultado_analisis = {
    'alarma_fuga': 'NO DETECTADA',
    'posicion_fuga': 0.0,
    'ultima_actualizacion': None
}

def cargar_datos():
    """Cargar datos existentes"""
    global paquetes_tarjeta1, paquetes_tarjeta2
    if os.path.exists(ARCHIVO_DATOS):
        try:
            with open(ARCHIVO_DATOS, 'r') as f:
                data = json.load(f)
                paquetes_tarjeta1 = data.get('tarjeta1', [])
                paquetes_tarjeta2 = data.get('tarjeta2', [])
            print(f"✅ Cargados {len(paquetes_tarjeta1)} paquetes T1, {len(paquetes_tarjeta2)} paquetes T2")
        except Exception as e:
            print(f"Error cargando: {e}")

def guardar_datos():
    """Guardar datos"""
    try:
        with open(ARCHIVO_DATOS, 'w') as f:
            json.dump({
                'tarjeta1': paquetes_tarjeta1,
                'tarjeta2': paquetes_tarjeta2
            }, f)
    except Exception as e:
        print(f"Error guardando: {e}")

def agregar_paquete(tarjeta_id, paquete):
    """Agregar paquete y mantener máximo 60"""
    if tarjeta_id == 1:
        paquetes_tarjeta1.append(paquete)
        if len(paquetes_tarjeta1) > MAX_PAQUETES:
            paquetes_tarjeta1.pop(0)
    else:
        paquetes_tarjeta2.append(paquete)
        if len(paquetes_tarjeta2) > MAX_PAQUETES:
            paquetes_tarjeta2.pop(0)
    guardar_datos()

def verificar_recepcion_datos():
    """Verificar si se están recibiendo datos (2 paquetes/segundo mínimo)"""
    ahora = time.time()
    estado = {'tarjeta1': True, 'tarjeta2': True}
    
    if paquetes_tarjeta1:
        ultimo_t1 = paquetes_tarjeta1[-1]['timestamp']
        if ahora - ultimo_t1 > 0.5:
            estado['tarjeta1'] = False
    else:
        estado['tarjeta1'] = False
    
    if paquetes_tarjeta2:
        ultimo_t2 = paquetes_tarjeta2[-1]['timestamp']
        if ahora - ultimo_t2 > 0.5:
            estado['tarjeta2'] = False
    else:
        estado['tarjeta2'] = False
    
    return estado

# Template HTML completo
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔧 Sistema de Detección de Fugas</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, sans-serif; 
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        h1 { 
            text-align: center; 
            color: #00d9ff;
            margin-bottom: 20px;
            font-size: 2.5em;
            text-shadow: 0 0 10px rgba(0,217,255,0.5);
        }
        
        .alert-panel {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .alert-status {
            font-size: 3em;
            font-weight: bold;
            margin: 20px 0;
            text-shadow: 0 0 20px rgba(255,255,255,0.5);
        }
        .leak-position {
            font-size: 2em;
            color: #ffd700;
        }
        
        .controls {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .btn {
            background: #00d9ff;
            color: #1a1a2e;
            border: none;
            padding: 15px;
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.3s;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,217,255,0.5); }
        .btn-danger { background: #ff4757; color: white; }
        .btn-success { background: #2ed573; color: white; }
        
        .status-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .status-card {
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            border: 2px solid #0f3460;
        }
        .status-card h3 { color: #00d9ff; margin-bottom: 10px; }
        .status-value { font-size: 2em; font-weight: bold; }
        .status-ok { color: #2ed573; }
        .status-error { color: #ff4757; }
        
        .charts-container {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        .chart-wrapper {
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            border: 2px solid #0f3460;
        }
        .chart-wrapper h3 {
            color: #00d9ff;
            margin-bottom: 15px;
            text-align: center;
        }
        canvas { width: 100% !important; height: 300px !important; }
        
        @media (max-width: 1200px) {
            .charts-container { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 Sistema de Detección de Fugas en Tuberías</h1>
        
        <div class="alert-panel">
            <h2>ESTADO DEL SISTEMA</h2>
            <div class="alert-status" id="alarmaStatus">{{ alarma }}</div>
            <div class="leak-position">Posición de fuga: <span id="posicionFuga">{{ posicion }}</span> metros</div>
            <div style="margin-top: 20px; opacity: 0.8;">Última actualización: <span id="ultimaActualizacion">{{ ultima_act }}</span></div>
        </div>
        
        <div class="status-cards">
            <div class="status-card">
                <h3>📦 Tarjeta 1</h3>
                <div class="status-value" id="paquetesT1">{{ paquetes_t1 }}</div>
                <div>paquetes almacenados</div>
                <div id="estadoT1" class="status-ok" style="margin-top: 10px;">✅ Recibiendo datos</div>
            </div>
            <div class="status-card">
                <h3>📦 Tarjeta 2</h3>
                <div class="status-value" id="paquetesT2">{{ paquetes_t2 }}</div>
                <div>paquetes almacenados</div>
                <div id="estadoT2" class="status-ok" style="margin-top: 10px;">✅ Recibiendo datos</div>
            </div>
            <div class="status-card">
                <h3>⏱️ Tiempo Muestreo</h3>
                <div class="status-value" id="tiempoMuestreo">{{ tiempo_muestreo }}</div>
                <div>milisegundos</div>
            </div>
            <div class="status-card">
                <h3>🕐 Hora Sistema</h3>
                <div class="status-value" style="font-size: 1.5em;" id="horaSistema">{{ hora_actual }}</div>
            </div>
        </div>
        
        <div class="controls">
            <button class="btn btn-success" onclick="generarDatosAleatorios()">🎲 Generar 10 Paquetes Aleatorios</button>
            <button class="btn btn-success" onclick="duplicarT1aT2()">📋 Duplicar T1 → T2</button>
            <button class="btn" onclick="actualizarGraficas()">🔄 Actualizar Gráficas</button>
            <button class="btn btn-danger" onclick="limpiarDatos()">🗑️ Limpiar Datos</button>
        </div>
        
        <h2 style="color: #00d9ff; margin: 30px 0 20px;">📊 Gráficas de Flujo (L/min)</h2>
        <div class="charts-container">
            <div class="chart-wrapper"><h3>Flujo 1</h3><canvas id="chartFlujo1"></canvas></div>
            <div class="chart-wrapper"><h3>Flujo 2</h3><canvas id="chartFlujo2"></canvas></div>
            <div class="chart-wrapper"><h3>Flujo 3</h3><canvas id="chartFlujo3"></canvas></div>
            <div class="chart-wrapper"><h3>Flujo 4</h3><canvas id="chartFlujo4"></canvas></div>
            <div class="chart-wrapper"><h3>Flujo 5</h3><canvas id="chartFlujo5"></canvas></div>
            <div class="chart-wrapper"><h3>Flujo 6</h3><canvas id="chartFlujo6"></canvas></div>
        </div>
        
        <h2 style="color: #00d9ff; margin: 30px 0 20px;">💧 Gráficas de Presión (m.c.a)</h2>
        <div class="charts-container">
            <div class="chart-wrapper"><h3>Presión 1</h3><canvas id="chartPresion1"></canvas></div>
            <div class="chart-wrapper"><h3>Presión 2</h3><canvas id="chartPresion2"></canvas></div>
            <div class="chart-wrapper"><h3>Presión 3</h3><canvas id="chartPresion3"></canvas></div>
            <div class="chart-wrapper"><h3>Presión 4</h3><canvas id="chartPresion4"></canvas></div>
            <div class="chart-wrapper"><h3>Presión 5</h3><canvas id="chartPresion5"></canvas></div>
            <div class="chart-wrapper"><h3>Presión 6</h3><canvas id="chartPresion6"></canvas></div>
        </div>
    </div>

    <script>
        let charts = {};
        
        function initCharts() {
            const chartConfig = (title) => ({
                type: 'line',
                data: { labels: [], datasets: [{ label: title, data: [], borderColor: '#00d9ff', tension: 0.4, fill: false }] },
                options: { 
                    responsive: true, 
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true, grid: { color: '#0f3460' } }, x: { grid: { color: '#0f3460' } } },
                    plugins: { legend: { labels: { color: '#eee' } } }
                }
            });
            
            for (let i = 1; i <= 6; i++) {
                charts[`flujo${i}`] = new Chart(document.getElementById(`chartFlujo${i}`), chartConfig(`Flujo ${i}`));
                charts[`presion${i}`] = new Chart(document.getElementById(`chartPresion${i}`), chartConfig(`Presión ${i}`));
            }
        }
        
        async function actualizarGraficas() {
            const response = await fetch('/obtener_ultimos_paquetes');
            const data = await response.json();
            
            for (let i = 1; i <= 6; i++) {
                charts[`flujo${i}`].data.labels = data.labels;
                charts[`flujo${i}`].data.datasets[0].data = data[`flujo${i}`];
                charts[`flujo${i}`].update();
                
                charts[`presion${i}`].data.labels = data.labels;
                charts[`presion${i}`].data.datasets[0].data = data[`presion${i}`];
                charts[`presion${i}`].update();
            }
            
            document.getElementById('paquetesT1').textContent = data.paquetes_t1;
            document.getElementById('paquetesT2').textContent = data.paquetes_t2;
            document.getElementById('tiempoMuestreo').textContent = data.tiempo_muestreo;
            document.getElementById('alarmaStatus').textContent = data.alarma;
            document.getElementById('posicionFuga').textContent = data.posicion_fuga;
            document.getElementById('ultimaActualizacion').textContent = data.ultima_actualizacion || 'N/A';
            
            if (data.estado_t1) {
                document.getElementById('estadoT1').innerHTML = '✅ Recibiendo datos';
                document.getElementById('estadoT1').className = 'status-ok';
            } else {
                document.getElementById('estadoT1').innerHTML = '❌ Sin datos';
                document.getElementById('estadoT1').className = 'status-error';
            }
            
            if (data.estado_t2) {
                document.getElementById('estadoT2').innerHTML = '✅ Recibiendo datos';
                document.getElementById('estadoT2').className = 'status-ok';
            } else {
                document.getElementById('estadoT2').innerHTML = '❌ Sin datos';
                document.getElementById('estadoT2').className = 'status-error';
            }
        }
        
        async function generarDatosAleatorios() {
            await fetch('/generar_aleatorios', { method: 'POST' });
            actualizarGraficas();
        }
        
        async function duplicarT1aT2() {
            await fetch('/duplicar_t1_t2', { method: 'POST' });
            actualizarGraficas();
        }
        
        async function limpiarDatos() {
            if (confirm('¿Eliminar todos los datos?')) {
                await fetch('/limpiar', { method: 'POST' });
                actualizarGraficas();
            }
        }
        
        setInterval(() => {
            document.getElementById('horaSistema').textContent = new Date().toLocaleTimeString();
        }, 1000);
        
        initCharts();
        actualizarGraficas();
        setInterval(actualizarGraficas, 10000);
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    estado = verificar_recepcion_datos()
    tiempo_muestreo = paquetes_tarjeta1[0]['mediciones'][0]['tiempo_muestreo'] if paquetes_tarjeta1 else 100
    
    return render_template_string(HTML_TEMPLATE,
        alarma=resultado_analisis['alarma_fuga'],
        posicion=resultado_analisis['posicion_fuga'],
        ultima_act=resultado_analisis['ultima_actualizacion'],
        paquetes_t1=len(paquetes_tarjeta1),
        paquetes_t2=len(paquetes_tarjeta2),
        tiempo_muestreo=tiempo_muestreo,
        hora_actual=datetime.now().strftime('%H:%M:%S')
    )

@app.route('/recibir_paquete', methods=['POST'])
def recibir_paquete():
    """Recibe paquetes de Arduino"""
    try:
        datos = request.get_data(as_text=True)
        lineas = datos.strip().split('\n')
        
        if lineas[0] != 'PAQUETE' or lineas[-1] != 'FIN_PAQUETE':
            return jsonify({'error': 'Formato inválido'}), 400
        
        tiempo = lineas[1].split(',')
        hora, minuto, segundo = int(tiempo[0]), int(tiempo[1]), int(tiempo[2])
        
        tarjeta_line = lineas[2]
        tarjeta_id = int(tarjeta_line.replace('TARJETA', ''))
        
        mediciones = []
        for i in range(3, 203):
            valores = lineas[i].split(',')
            mediciones.append({
                'tiempo_muestreo': int(valores[0]),
                'flujos': [float(valores[j]) for j in range(1, 7)],
                'presiones': [float(valores[j]) for j in range(7, 13)]
            })
        
        paquete = {
            'timestamp': time.time(),
            'hora_inicio': f"{hora:02d}:{minuto:02d}:{segundo:02d}",
            'mediciones': mediciones
        }
        
        agregar_paquete(tarjeta_id, paquete)
        print(f"✅ Paquete recibido de Tarjeta {tarjeta_id}")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/obtener_ultimos_paquetes', methods=['GET'])
def obtener_ultimos_paquetes():
    """Obtiene últimos 10 paquetes para gráficas"""
    estado = verificar_recepcion_datos()
    
    todos_paquetes = []
    for p in paquetes_tarjeta1[-10:]:
        todos_paquetes.append(('T1', p))
    for p in paquetes_tarjeta2[-10:]:
        todos_paquetes.append(('T2', p))
    
    todos_paquetes.sort(key=lambda x: x[1]['timestamp'])
    
    labels = [f"{p[0]} {p[1]['hora_inicio']}" for p in todos_paquetes[-10:]]
    
    flujos = {f'flujo{i}': [] for i in range(1, 7)}
    presiones = {f'presion{i}': [] for i in range(1, 7)}
    
    for _, paquete in todos_paquetes[-10:]:
        for i in range(6):
            flujo_prom = sum(m['flujos'][i] for m in paquete['mediciones']) / 200
            presion_prom = sum(m['presiones'][i] for m in paquete['mediciones']) / 200
            presion_mca = presion_prom * 2.0
            
            flujos[f'flujo{i+1}'].append(round(flujo_prom, 2))
            presiones[f'presion{i+1}'].append(round(presion_mca, 2))
    
    tiempo_muestreo = paquetes_tarjeta1[0]['mediciones'][0]['tiempo_muestreo'] if paquetes_tarjeta1 else 100
    
    return jsonify({
        'labels': labels,
        **flujos,
        **presiones,
        'paquetes_t1': len(paquetes_tarjeta1),
        'paquetes_t2': len(paquetes_tarjeta2),
        'tiempo_muestreo': tiempo_muestreo,
        'alarma': resultado_analisis['alarma_fuga'],
        'posicion_fuga': resultado_analisis['posicion_fuga'],
        'ultima_actualizacion': resultado_analisis['ultima_actualizacion'],
        'estado_t1': estado['tarjeta1'],
        'estado_t2': estado['tarjeta2']
    })

@app.route('/generar_aleatorios', methods=['POST'])
def generar_aleatorios():
    """Genera 10 paquetes aleatorios de prueba"""
    import random
    tarjeta = random.choice([1, 2])
    
    for _ in range(10):
        mediciones = []
        for j in range(200):
            mediciones.append({
                'tiempo_muestreo': j * 100,
                'flujos': [random.uniform(10, 50) for _ in range(6)],
                'presiones': [random.uniform(1.0, 4.5) for _ in range(6)]
            })
        
        paquete = {
            'timestamp': time.time(),
            'hora_inicio': datetime.now().strftime('%H:%M:%S'),
            'mediciones': mediciones
        }
        
        agregar_paquete(tarjeta, paquete)
        time.sleep(0.1)
    
    return jsonify({'status': 'success'})

@app.route('/duplicar_t1_t2', methods=['POST'])
def duplicar_t1_t2():
    """Duplica datos de T1 a T2"""
    global paquetes_tarjeta2
    paquetes_tarjeta2 = paquetes_tarjeta1.copy()
    guardar_datos()
    return jsonify({'status': 'success'})

@app.route('/limpiar', methods=['POST'])
def limpiar():
    """Limpia todos los datos"""
    global paquetes_tarjeta1, paquetes_tarjeta2
    paquetes_tarjeta1 = []
    paquetes_tarjeta2 = []
    guardar_datos()
    return jsonify({'status': 'success'})

@app.route('/obtener_datos_raspberry', methods=['GET'])
def obtener_datos_raspberry():
    """Raspberry Pi obtiene datos en orden de llegada"""
    todos = []
    for p in paquetes_tarjeta1:
        todos.append({'tarjeta': 1, 'paquete': p})
    for p in paquetes_tarjeta2:
        todos.append({'tarjeta': 2, 'paquete': p})
    
    todos.sort(key=lambda x: x['paquete']['timestamp'])
    
    return jsonify({'paquetes': todos})

@app.route('/borrar_datos_procesados', methods=['POST'])
def borrar_datos_procesados():
    """Raspberry borra datos después de procesar"""
    global paquetes_tarjeta1, paquetes_tarjeta2
    paquetes_tarjeta1 = []
    paquetes_tarjeta2 = []
    guardar_datos()
    return jsonify({'status': 'success'})

@app.route('/actualizar_analisis', methods=['POST'])
def actualizar_analisis():
    """Raspberry actualiza resultado del análisis"""
    global resultado_analisis
    data = request.get_json()
    resultado_analisis = {
        'alarma_fuga': data.get('alarma_fuga', 'NO DETECTADA'),
        'posicion_fuga': data.get('posicion_fuga', 0.0),
        'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    return jsonify({'status': 'success'})

# Cargar datos al iniciar
cargar_datos()

# Para desarrollo local
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)