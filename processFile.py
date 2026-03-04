import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd
import time

logRate = 5  # times per second

# Load and process data
dataFile = open("Example Data Sets\\VacuumTestData.txt")
data = dataFile.read()

def processData(data):
    data = data.splitlines()
    return [float(x) for x in data if x.strip()]

def getTime(t):
    time = len(t) / logRate
    return time

# Graph takes an input of data points as a list
pressure_values = processData(data)
runTime = getTime(pressure_values)
print(f"Total recording time: {str(runTime)} Seconds")
print(f"Total data points: {len(pressure_values)}")

# Create Dash app
app = dash.Dash(__name__)

# App layout
app.layout = html.Div(
    # full-screen dark background container
    style={
        'backgroundColor': "#181818",
        'color': '#e0e0e0',
        'minHeight': '100vh',
        'minWidth': '100vw',
        'width': '100vw',
        'height': '100vh',
        'fontFamily': 'Courier New, monospace',
        'margin': '0',
        'padding': '0',
    },
    children=[
        html.H1("Pressure Data Logger Dashboard", 
                style={
                    'textAlign': 'center', 
                    'marginBottom': 30, 
                    'paddingTop': 20,
                    'color': '#00d4ff',
                    'fontFamily': 'Courier New, monospace'
                }),
        
        html.Div([
            html.Div([
                html.H3(f"Total Duration: {runTime:.1f}s"),
                html.H3(f"Data Points: {len(pressure_values)}"),
                html.H3(f"Sample Rate: {logRate} Hz"),
            ], style={
                'display': 'flex', 
                'justifyContent': 'space-around', 
                'marginBottom': 30, 
                'flexWrap': 'wrap',
                'color': '#e0e0e0',
                'fontFamily': 'Courier New, monospace'
            }),
            
            dcc.Graph(id='pressure-graph', style={'height': '800px', 'marginBottom': 20}),
            
            html.Div([
                html.Label("Show Points:", style={'color': '#e0e0e0', 'fontSize': '16px'}),
                dcc.Slider(
                    id='data-slider',
                    min=10,
                    max=len(pressure_values),
                    step=10,
                    value=len(pressure_values),
                    marks={i: str(i) for i in range(0, len(pressure_values), max(1, len(pressure_values)//5))},
                    updatemode='drag'
                ),
            ], style={'marginTop': 30, 'marginBottom': 20, 'paddingRight': 20, 'paddingLeft': 20}),
            
        ], style={'padding': '20px', 'margin': 'auto'}),
    ]
)

# Callback to update graph
@app.callback(
    Output('pressure-graph', 'figure'),
    Input('data-slider', 'value')
)
def update_graph(num_points):
    # Calculate time axis
    time_axis = [i / logRate for i in range(num_points)]
    pressure_subset = pressure_values[:num_points]
    
    # Create figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=time_axis,
        y=pressure_subset,
        mode='lines+markers',
        name='Pressure',
        hovertemplate='<b>Time:</b> %{x:.2f}s<br><b>Pressure:</b> %{y:.2f} Pa<extra></extra>',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=4)
    ))
    
    fig.update_layout(
        title='Pressure Over Time',
        xaxis_title='Time (seconds)',
        yaxis_title='Pressure (Pa)',
        hovermode='x unified',
        template='plotly_dark',
        height=600,
        font=dict(family="Courier New", size=12),
        title_font=dict(family="Arial Black", size=24)
    )
    
    return fig

if __name__ == '__main__':
    print(f"\nStarting Dash server...")
    print(f"Open your browser to http://127.0.0.1:8050")
    app.run(debug=True)