from ctypes import sizeof
import logging
import asyncio
import platform
import ast
import struct
from time import sleep
from tkinter.tix import Tree
from pygltflib import GLTF2
from bleak import BleakClient
from bleak import BleakScanner
from bleak import discover
from numpy import record
from datetime import datetime
import pandas as pd
import datetime
import time
import dash_daq as daq
import dash_vtk
import dash
from dash import dcc, html,dash_table
import plotly
from dash.dependencies import Input, Output, State
from bson.objectid import ObjectId
from dash.exceptions import PreventUpdate
from flask import Flask, Response
import cv2
#--------------------------------mongo db---------------------------------------
import pymongo
import datetime
client = pymongo.MongoClient("mongodb+srv://guillermogarcia:5dzUggxRzfhvNLWQ@cluster0.vk1oofk.mongodb.net/?retryWrites=true&w=majority")
db = client["Ejercicios"]
collection = db["Ejercicios"]

#--------------------------------variables globales---------------------------------------
record = {
    "Nombre":"",
    "Ejercicio": "",
    "Repeticiones": 0,
    "Series": 0,
    "Superior": 0,
    "Inferior": 0,
    "Valores":[],
    "Fecha":"",
    "Hora":""
}
margenSuperior = {
    'subida' : False,
    'bajada' : False
}
margenInferior = {
    'subida' : False,
    'bajada' : False
}
compensacion = 0
Vini = 0
descanso = False
finalEjercicio = False
n_descanso = 0
contadorReps = 0
serieActual = 0
boton_monitorizar = False
hayMovimiento = False

sensor = (0,0,0)
accelerometro = (0,0,0)
dataOrientacion = {
    'time': [],
    'X': [],
    'Y': [],
    'Z': []
}
dataAccel = {
    'time': [],
    'X': [],
    'Y': [],
    'Z': []
}

#---------------------------------------Archivo 3D------------------------------------------

with open("datasets/cow.obj", 'r') as file:
    txt_content = file.read()
    
#--------------------------------------BLE get data-----------------------------------------

async def readValues(client):
    valr = await client.read_gatt_char(ORI_VAL)
    x= struct.unpack('<3h', valr)
    valrAccel = await client.read_gatt_char(ACCEL_VAL)
    a = struct.unpack('<3f', valrAccel)

    global sensor
    global accelerometro
    
    accelerometro = a
    sensor = x

address = "A1:54:24:03:F6:AE"
ORI_VAL = "19b10000-9001-537e-4f6c-d104768a1214"
ACCEL_VAL = "19b10000-6001-537e-4f6c-d104768a1214"

def callback(sender: int, data: bytearray):
    pass 

async def ble():
    print('NICLA SENSE ME')
    print('Looking for BLESense-F6AE Peripheral Device...')

    found = False
    client = BleakClient(address)
    try:
        await client.connect()
        print('Conectado!')
        await client.start_notify(ORI_VAL, callback)
        await client.start_notify(ACCEL_VAL, callback)
        while True:
           await readValues(client)
    except Exception as e:
        print(e)


import threading
def between_callback():
    asyncio.run(ble())

#------------------------------------------------Camera---------------------------------------------------

class VideoCamera(object):
    def __init__(self):
        self.video = cv2.VideoCapture(0)

    def __del__(self):
        self.video.release()

    def get_frame(self):
        success, image = self.video.read()
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()


def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

server = Flask(__name__)
@server.route('/video_feed')
def video_feed():
    return Response(gen(VideoCamera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

#------------------------------------------------Dashboard--------------------------------------------

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


app = dash.Dash(__name__, external_stylesheets=external_stylesheets,server=server)

tab1 = html.Div([
    html.Div(children=[
        html.H2('Sensorización movimientos UCI'),
        html.Label('Nombre del paciente'),
        dcc.Input(value='', type='text',id='name-input'),
        html.Label('Ejercicio'),
        dcc.Dropdown(['Codo al hombro izquierdo', 'Codo al hombro derecho','Brazo izquierdo al techo','Brazo derecho al techo','Pie hacia la rodilla','Pie derecho hacia la rodilla','Pie izquierdo hacia la rodilla','Levantamiento de pierna izquierda','Levantamiento de pierna derecha'],id='selector-ejercicio'),

        html.Br(),
        html.Div([
            html.Div([
                html.Label('Número de repeticiones'),
                dcc.Input(value='10', type='number',id='reps-input'),
            ]),
            html.Div([
                html.Label('Número de series'),
                dcc.Input(value='2', type='number',id='series-input'),
            ]),
            html.Div([
                html.Label('Descanso entre series (segundos)'),
                dcc.Input(value='5', type='number',id='descanso-input'),
            ])
        ],style={'display': 'flex', 'flex-direction': 'row'}),
       
        html.Div([
            html.Div(
                [html.Label('Ángulo superior a superar'),
                dcc.Input(value='90', type='number',id='max-angle-input'),
            ]),
            html.Div([
                html.Label('Ángulo inferior a superar'),
                dcc.Input(value='-90', type='number',id='min-angle-input')
            ]),
            
           ], 
        style={'display': 'flex', 'flex-direction': 'row'}),
        dcc.Checklist(id='compensacion-check',options=
            ['Valores compensados'],
        ),
        html.Br(),
        html.Button('Comenzar monitorización', id='submit-start', n_clicks=0),
    ], style={'padding': 10, 'flex': 1}),

    html.Div(children=[
        html.Br(),
         
            html.Div([
                html.Div(children=[
                html.Img(src="/video_feed")
                ], style={'padding': 10, 'flex': 1}),

                html.Div(children=[
                    dash_vtk.View(
                        id="click-info-view",
                        children=[
                            dash_vtk.GeometryRepresentation(id="arm-geometry", children=[
                                dash_vtk.Reader(
                                    vtkClass="vtkOBJReader",
                                    parseAsText=txt_content,
                                ),
                            ],
                            actor= {'orientation': (-sensor[0],0,0)}
                            ),
                        ],
                    )
                ], style={'padding': 10, 'flex': 1})
            ], style={'display': 'flex', 'flex-direction': 'row'}),
        html.Div(id='live-update-model'),
        html.Div(id='live-update-ori'),
        html.Div(id='pruebisima'),
        dcc.Interval(
            id='interval-component',
            interval=0.2*1000, # in milliseconds
            n_intervals=0,
            disabled = True
        ),
    ], style={'padding': 10, 'flex': 1})
], style={'display': 'flex', 'flex-direction': 'row'})

tab2 = html.Div([
    html.H1('Historial de ejercicios'),
    dcc.Interval(id='interval_db',interval = 86400000 * 7,n_intervals = 0),
    html.Div(id='historial-ejercicios'),
    html.Div(id='historial-grafico')
]) 

app.layout =  html.Div([
    dcc.Tabs(id='tabs-main',children=[
        dcc.Tab(id='tab1',label='Monitorizar ejercicio', children=[
            tab1
        ]),
        dcc.Tab(id='tab2',label='Historial ejercicios', children=[
            tab2
        ])
    ])
])






#Callback mongodb
@app.callback(
    Output('historial-ejercicios', 'children'),
    Input('tabs-main', 'value')
)
def getDataMongoDB(tabs):
    df = pd.DataFrame(list(collection.find()))
    df['_id'] = df['_id'].astype(str)
    if tabs == 'tab-2':
        return[
        dash_table.DataTable(
            id='tabla-ejercicios',
            data = df.to_dict('records'),
            hidden_columns=['Valores','_id'],
            page_size=10,
            css=[{"selector": ".show-hide", "rule": "display: none"}]
        ),
        ]
    return  dash_table.DataTable(
            id='tabla-ejercicios')


#Callback click en tabla
@app.callback(
    Output('historial-grafico', 'children'),
    Input('tabla-ejercicios', 'active_cell'),
    Input('tabla-ejercicios', "derived_virtual_data"),
)
def clickTabla(active_cell,data):
    active_row = active_cell['row'] if active_cell else None
    if(active_row is not None):
        y = data[active_row]['Valores']
        X = list(range(len(y)))
        fig = plotly.tools.make_subplots(rows=1, cols=1, vertical_spacing=0.2)
        fig['layout']['margin'] = {
            'l': 30, 'r': 10, 'b': 30, 't': 10
        }
        fig['layout']['legend'] = {'x': 0, 'y': 1, 'xanchor': 'left'}

        fig.append_trace({
            'x': X,
            'y': y,
            'name': 'X',
            'mode': 'lines+markers',
            'type': 'scatter'
        }, 1, 1)
        return html.Br(),html.H1('Orientación del sensor'),dcc.Graph(id='live-update-graph',figure=fig)
    return ''

#Callback para iniciar o parar el ejercicio
@app.callback(
    [Output('interval-component', 'disabled'),
    Output('interval-component', 'n_intervals'),
    Output('submit-start', 'children')],
    Input('submit-start', 'n_clicks')
)
def update_output(n_clicks):
    global puntosMal
    global Vini
    global contadorReps
    global compensacion
    global descanso
    if n_clicks is None:
        raise PreventUpdate
    if(n_clicks != 0):
        if(n_clicks%2 == 1):
            return False,0, 'PARAR MONITORIZACIÓN'
        else:
            inf,sup = comprobarPicos()
            puntosMal = 0
            Vini = 0
            global record
            collection.insert_one(record)
            compensacion = 0
            dataOrientacion['X'].clear()
            dataOrientacion['Y'].clear()
            dataOrientacion['Z'].clear()
            dataAccel['X'].clear()
            dataAccel['Y'].clear()
            dataAccel['Z'].clear()
            dataOrientacion['time'].clear()
            contadorReps = 0
            descanso = False

            return True,0, 'COMENZAR MONITORIZACIÓN'
    else: 
        return True,0,'COMENZAR MONITORIZACIÓN'

#Callback para modificar los parametros según la etiqueta
@app.callback(
    [Output('max-angle-input', 'value'),
    Output('min-angle-input', 'value')],
    Input('selector-ejercicio','value')
)
def modificar_parametros(ejercicio):
    
    if(ejercicio =='Codo al hombro'):
        return 1,2
    elif (ejercicio == 'Brazo al techo'):
        return 90,-30
    elif (ejercicio == 'Pie hacia la rodilla'):
        return 100, 0
    elif (ejercicio == 'Levantamiento de pierna'):
        return 100,0
    else:
        return 90,-90


#Callback principal, donde en función del intervalo se muestran las metricas del ejercicio
@app.callback(Output('live-update-ori', 'children'),
            Input('interval-component', 'n_intervals'),
            State('selector-ejercicio','value'),
            State('max-angle-input', 'value'),
            State('min-angle-input', 'value'),
            State('reps-input','value'),
            State('compensacion-check','value'),
            State('series-input','value'),
            State('descanso-input','value'),
            State('name-input','value')
            
            )
def update_metrics(n,ejercicio,max_val,min_val,reps,compCheck,series,descansoEstablecido,nombrePaciente):

    global puntosMal,compensacion,hayMovimiento,serieActual,descanso,dataOrientacion,contadorReps,Vini,finalEjercicio
    #Primeras iteraciones para mostrar una cuenta atrás
    if(n != 0):
        led3 = daq.LEDDisplay(
            id='my-LED-display-1',
            value='3',
            size=100,
        )
        led2 = daq.LEDDisplay(
            id='my-LED-display-1',
            value='2',
            size=100,
        )
        led1 = daq.LEDDisplay(
            id='my-LED-display-1',
            value='1',
            size=100,
        )

        if(n < 5):
            return  led3
        elif(n < 10):
            return led2
        elif (n < 15):
            #actualizamos compensacion
            x,_,_ = sensor
            compensacion = 0 - (-x)
            serieActual = 1
            return led1 
            
        else:
            if (not finalEjercicio):
                #Si no está en etapa de descanso procede a evaular el ejercicio
                if (not descanso):
                    #Iteraciones de monitorización
                    #----------------------------Dash----------------------------

                    
                    # Collect some data
                    time = datetime.datetime.now() 
                    x,_,_ = sensor
                    xa,ya,za = accelerometro
                    
                    if(compCheck is not None):
                        if(compCheck[0] == 'Valores compensados'):
                            dataOrientacion['X'].append(-x + compensacion)
                        else:
                            dataOrientacion['X'].append(-x)
                    else:
                        dataOrientacion['X'].append(-x)
                    dataOrientacion['Y'].append(max_val)
                    dataOrientacion['Z'].append(min_val)
                    dataAccel['X'].append(xa)
                    dataAccel['Y'].append(ya)
                    dataAccel['Z'].append(za)
                    dataOrientacion['time'].append(time)
                    numMuestras = 50
                    auxX = dataOrientacion['X'][-numMuestras:]
                    auxMax = dataOrientacion['Y'][-numMuestras:]
                    auxMin = dataOrientacion['Z'][-numMuestras:]
                    auxTime = dataOrientacion['time'][-numMuestras:]
                    # Create the graph with subplots
                    fig = plotly.tools.make_subplots(rows=1, cols=1, vertical_spacing=0.2)
                    fig['layout']['margin'] = {
                        'l': 30, 'r': 10, 'b': 30, 't': 10
                    }
                    fig['layout']['legend'] = {'x': 0, 'y': 1, 'xanchor': 'left'}



                    fig.append_trace({
                        'x': auxTime,
                        'y': auxMax,
                        'name': 'Umbral superior',
                        'mode': 'lines+markers',
                        'type': 'scatter'
                    }, 1, 1)
                    fig.append_trace({
                        'x': auxTime,
                        'y': auxX,
                        'name': 'Sensor orientación',
                        'mode': 'lines+markers',
                        'type': 'scatter'
                    }, 1, 1)
                    fig.append_trace({
                        'x': auxTime,
                        'y': auxMin,
                        'name': 'Umbral inferior',
                        'mode': 'lines+markers',
                        'type': 'scatter'
                    }, 1, 1)
                    

                    # fig2 = plotly.tools.make_subplots(rows=1, cols=1, vertical_spacing=0.2)
                    # fig2['layout']['margin'] = {
                    #     'l': 30, 'r': 10, 'b': 30, 't': 10
                    # }
                    # fig2['layout']['legend'] = {'x': 0, 'y': 1, 'xanchor': 'left'}
                    # fig2.append_trace({
                    #     'x': dataOrientacion['time'],
                    #     'y': dataAccel['Y'],
                    #     'name': 'Y',
                    #     'mode': 'lines+markers',
                    #     'type': 'scatter'
                    # }, 1, 1)

                    # hayMovimiento = comprobarMovimiento(ya)
                    # contadorReps += repeticiones(ya)
                    contadorReps += subidasYbajadas(max_val,min_val)
                    contadorLed = daq.LEDDisplay(
                        id='repeticiones-led',
                        value=int(contadorReps),
                        size=100,
                    )
                    global record,margenInferior,margenSuperior
                    now = datetime.datetime.now()
                    hora = now.strftime("%H:%M:%S")
                    date = now.strftime("%d-%m-%Y")
                    print(nombrePaciente,ejercicio)
                    record = {
                        "Nombre":nombrePaciente,
                        "Ejercicio": ejercicio,
                        "Repeticiones": contadorReps,
                        "Series": serieActual,
                        "Superior": max_val,
                        "Inferior": min_val,
                        "Valores":dataOrientacion['X'],
                        "Fecha":date,
                        "Hora":hora
                    }
                    msText = "--"
                    miText = "--"
                    if(margenSuperior['bajada'] == True and margenSuperior['subida'] == True):
                        msText = 'COMPLETADO' 
                    else:
                        msText = '--'
                    if(margenInferior['bajada'] == True and margenInferior['subida'] == True):
                        miText = 'COMPLETADO' 
                    else:
                        miText = '--'
                    led = html.Div([
                        html.H2('Movimiento superior: ' + msText),html.H2('Movimiento inferior: '+ miText)
                        ])

                    #Si alcanza la meta de repeticiones entra en estado de descanso durante el tiempo establecido o si es la última serie se termina el ejercicio
                    if (reps == contadorReps):
                        print(series,serieActual)
                        if(int(series) == int(serieActual)):
                            finalEjercicio = True
                            contadorReps = 0
                            serieActual = 0
                            descanso = False
                        else:
                            serieActual += 1
                            descanso = True
                            contadorReps = 0
                        
                    return html.H1('SERIE '+ str(serieActual)),html.H3('ORIENTACIÓN'),dcc.Graph(id='live-update-graph',figure=fig),contadorLed,led
                else:
                    #Si está en estado de descanso
                    global n_descanso
                    #Intervalos de 0.2 segundos, por lo que cada 5 iteraciones son equivalentes a 1 segundo
                    if(int(n_descanso/5) == int(descansoEstablecido)):
                        #Descanso terminado
                        descanso = False
                        n_descanso = 0
                        #Comienza siguiente serie

                        return ''
                    else:
                        n_descanso +=1
                        descansoLED = daq.LEDDisplay(
                            id='my-LED-display-1',
                            value=int(n_descanso/5),
                            size=100,
                        )
                        return html.H2("¡Toca descansar!"),descansoLED
            else:
                return html.H1("¡Ejercicio completado!"),html.H4("Para terminar el ejercicio y guardar el progreso pulse el botón de terminar ejercicio")
    else:
        return ''



#Fucncion para detectar subidas y bajadas
def subidasYbajadas(max, min):
    global margenInferior,margenSuperior,dataOrientacion
    if len(dataOrientacion['X']) >= 2 :
        aux = dataOrientacion['X'][-2:]
        #Aux es un array auxiliar que contiene los dos ultimos valores de las mediciones, siendo el elemento 0 la penultima medicion y el elemento 1 la ultima meidicion tomada
        
        #Margen superior
        if(aux[0]<= max and aux[1] >= max):
            #Si el penultimo elemento es menor al umbral superior y el ultimo elemento captado es mayor, es decir, está sobrepasando el umbral como una SUBIDA
            if(margenSuperior['subida'] == False):
                margenSuperior['subida'] = True
        elif(aux[0]>= max and aux[1] <= max):
            #Si el penultimo elemento es mayor al umbral superior y el ultimo elemento captado es menor, es decir, está sobre pasando el umbral como una BAJADA
            if(margenSuperior['bajada'] == False):
                margenSuperior['bajada'] = True
        

         #Margen infereior
        if(aux[0]>= min and aux[1] <= min):
            #Si el penultimo elemento es mayor al umbral inferior y el ultimo elemento captado es menjor, es decir, está sobrepasando el umbral como una BAJADA
            if(margenInferior['bajada'] == False):
                margenInferior['bajada'] = True
        elif(aux[0]<= min and aux[1] >= min):
            #Si el penultimo elemento es menor al umbral inferior y el ultimo elemento captado es mayor, es decir, está sobre pasando el umbral como una SUBIDA
            if(margenInferior['subida'] == False):
                margenInferior['subida'] = True
        
        #Putuacion
        if(margenInferior['bajada'] == True and margenInferior['subida'] == True and margenSuperior['bajada'] == True and margenSuperior['subida'] == True):
            margenInferior['bajada'] = False
            margenInferior['subida'] = False
            margenSuperior['bajada'] = False
            margenSuperior['subida'] = False
            return 1
        else:
            return 0


            
#Funcion para guardar los registros en la bbdd
def guardarRegistros(ejercicio, repeticiones, calidad,valores):
    global collection
    record = {
        "Ejercicio": ejercicio,
        "Repeticiones": repeticiones,
        "Calidad del ejercicio": calidad,
        "Valores": valores,
        "Fecha":datetime.datetime.now(datetime.timezone.utc)
    }
    collection.insert_one(record)

def comprobarPicos():
    #Funcion que devuelve los picos superiores e inferiores para su posterior analisis
    picosSuperiores = []
    picosInferiores = []
    detras = 0
    medio = 0
    for frente in dataOrientacion['X']:
        if(medio > detras and medio > frente):
            picosSuperiores.append(medio)
        elif(medio < detras and medio < frente):
            picosInferiores.append(medio)
        detras = medio
        medio = frente

    return picosInferiores,picosSuperiores

#Funcion para detectar si hay movimiento o no, Si sobrepasa un umbral determinado de aceleracion lo detectaremos como movimiento    
def comprobarMovimiento(accel):
    if(abs(accel)>250):
        return True
    else:
        return False

def repeticiones(accel):
    global dataOrientacion
    global hayMovimiento
    if len(dataOrientacion['X']) > 4 :
        if ((comprobarMovimiento(accel) == False) and (hayMovimiento == True)):
            #Cuando está con muy poco movimiento (puntos maximos o minimos) tras haber estado en movimiento
            aux = dataOrientacion['X'][-4:]
            if(aux[0] <= aux[1] <= aux[2] <= aux[3]):
                return 1
            elif (aux[0] >= aux[1] >= aux[2] >= aux[3]):
                return 1
            else:
                return 0
    return 0
# @app.callback(Output('click-info-view', 'children'),
#               Input('interval-component', 'n_intervals'))
# def moverBrazo(n):
#     global boton_monitorizar
#     x,y,z = sensor
#     if boton_monitorizar == False:
#         pass
#     else:
#         return dash_vtk.GeometryRepresentation(id="arm-geometry", children=[
#                         dash_vtk.Reader(
#                             vtkClass="vtkOBJReader",
#                             parseAsText=txt_content,
#                         ),
#                     ],
#                     actor= {'orientation': (-x,0,0)}
#                     )



#BLE recieving data in background
_thread = threading.Thread(target=between_callback)
_thread.start()

app.run_server(debug=False)