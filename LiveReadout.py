import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import plotly.graph_objects as go
import time
import threading
from collections import deque
from queue import Queue
import serial
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import socket


logRate = 5  # times per second
MAX_BUFFER_SIZE = 500  # Keep last 500 data points (~100 seconds at 5Hz)

# Thread-safe data buffer
data_buffer = deque(maxlen=MAX_BUFFER_SIZE)
data_lock = threading.Lock()
is_recording = False
connection_status = "Disconnected"
start_time = None
data_mode = None  # "live" or "file" or "wifi," live data mode means reading data over Serial.
loaded_file_data = None  # For file mode
loaded_file_path = None
arduino_ip = '192.168.1.100' # Make sure to set proper IP and port for your Arduino WiFi module
arduino_port = 12345


def receive_data_from_arduino(port='COM4', baudrate=9600, log_path='arduino_log.txt'):
    """
    Background thread function to receive data from Arduino and log to file.
    Modify port and baudrate based on your Arduino setup.
    """
    global connection_status, is_recording, start_time
    
    try:
        # Attempt to connect to Arduino
        ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)  # Wait for Arduino to initialize
        
        connection_status = "Connected"
        is_recording = True
        start_time = time.time()
        print(f"Connected to Arduino on {port}")
        
        # Open log file in append mode
        with open(log_path, 'a') as logfile:
            # logfile.write("# Arduino pressure log started at " + datetime.now().isoformat() + "\n")
            
            while is_recording:
                try:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8').strip()
                        if line:
                            try:
                                pressure_value = float(line)
                                with data_lock:
                                    data_buffer.append(pressure_value)
                                # write to log file with timestamp
                                # timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                                logfile.write(f"{pressure_value}\n")
                                logfile.flush()
                                print(f"[DEBUG] Received from Arduino: {pressure_value}")
                            except ValueError:
                                print(f"Could not parse: {line}")
                except Exception as e:
                    print(f"Error reading from serial: {e}")
                    connection_status = "Reading Error"
                    # connection lost
                    is_recording = False
                    break
        
        ser.close()
    except Exception as e:
        connection_status = f"Connection Error: {str(e)}"
        print(f"Failed to connect to Arduino: {e}")
def receive_wifi(ip, port, log_path='arduino_log.txt'):
    global connection_status, is_recording, start_time, sock
    
    try: # Connect to Arduino via Wifi
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((ip, port))

        time.sleep(2) # Wait for connection

        connection_status = "Connected"
        is_recording = True
        start_time = time.time()
        print(f"Connected to Arduino on {ip}:{port}")

        with open(log_path, 'a') as logfile:
            while is_recording:
                try:
                    data, addr = sock.recvfrom(1024) # buffer size
                    line = data.decode('utf-8').strip()
                    if line:
                        try:
                            pressure_value = float(line)
                            with data_lock:
                                data_buffer.append(pressure_value)
                            logfile.write(f"{pressure_value}\n")
                            logfile.flush()
                            print(f"[DEBUG] Received from Arduino: {pressure_value}")
                        except ValueError:
                            print(f"Could not parse: {line}")
                except Exception as e:
                    print(f"Error receiving from socket: {e}")
                    connection_status = "Reading Error"
                    is_recording = False
                    break
        sock.close()
    except Exception as e:
        connection_status = f"Connection Error: {str(e)}"
        print(f"Failed to connect to Arduino: {e}")
    
def load_file_data(file_path):
    """Load data from a file and populate the buffer."""
    global is_recording, start_time, connection_status, loaded_file_data, loaded_file_path
    
    try:
        with open(file_path, 'r') as f:
            data = f.read()
        
        data_lines = data.splitlines()
        pressure_values = [float(x) for x in data_lines if x.strip()]
        
        loaded_file_data = pressure_values
        loaded_file_path = file_path
        connection_status = "File Loaded"
        is_recording = True
        start_time = time.time()
        
        # Load all data into buffer
        with data_lock:
            for value in pressure_values:
                data_buffer.append(value)
        
        print(f"Loaded {len(pressure_values)} data points from {file_path}")
        
    except Exception as e:
        connection_status = f"File Error: {str(e)}"
        print(f"Failed to load file: {e}")

def show_startup_dialog():
    """Show a dialog to select between live data and file mode."""
    print("Select file for reading")
    global data_mode, loaded_file_path
    
    # Create hidden root window
    root = tk.Tk()
    root.withdraw()
    
    # Show selection dialog
    result = filedialog.askopenfilename(
        title="Select data source: Cancel for LIVE DATA, or select a file to load",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        parent=root
    )
    
    if result:
        # File was selected
        data_mode = "file"
        loaded_file_path = result
        root.destroy()
        load_file_data(result)
    else:
        # No file selected, use live mode
        data_mode = "live"
        root.destroy()
def mode_selection_dialog():
    """Show a dialog to select between live data, file mode, or wifi mode."""
    print("Select data source")
    global data_mode, loaded_file_path

    root = tk.Tk()
    root.title("Mode Selection")
    root.geometry("260x160")

    mode_var = tk.StringVar(value="file")

    def on_mode_selected():
        nonlocal root
        selected = mode_var.get()
        data_mode = selected

        if selected == "file":
            show_startup_dialog()

        root.destroy()

    frame = ttk.Frame(root, padding=12)
    frame.pack(fill="both", expand=True)

    label = ttk.Label(frame, text="Choose Mode")
    label.pack(anchor="w", pady=(0, 6))

    options = ["file", "live", "wifi"]
    for opt in options:
        rb = ttk.Radiobutton(
            frame,
            text=opt.capitalize(),
            variable=mode_var,
            value=opt,
            command=on_mode_selected
        )
        rb.pack(anchor="w", pady=2)

    root.mainloop()

    # Keep data_mode in sync with selected option
    if mode_var.get() in options:
        data_mode = mode_var.get()
        print(data_mode)
# (simulation removed – real Arduino data only)
def start_data_collection():
    """Start the background data collection thread."""
    if data_mode == "live":
        thread = threading.Thread(target=receive_data_from_arduino, args=('COM4', 9600), daemon=True)
        thread.start()
    elif data_mode == "file" and loaded_file_path:
        # File already loaded in startup dialog
        pass
    elif data_mode == "wifi":
        # For simplicity, using fixed IP and port. In a real application, you might want to ask the user for these.
        thread = threading.Thread(target=receive_wifi, args=(arduino_ip, arduino_port), daemon=True)
        thread.start()

# Create Dash app
app = dash.Dash(__name__)

# App layout
app.layout = html.Div(
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
        'overflow': 'hidden'
    },
    children=[
        # Hidden interval component for live updates
        dcc.Interval(
            id='live-update-interval',
            interval=200,  # Update every 200ms
            n_intervals=0
        ),
        
        # Hidden store to track elapsed time
        dcc.Store(id='elapsed-time-store', data=0),
        dcc.Store(id='data-mode-store', data=data_mode),
        
        html.H1(id='app-title', children="Pressure Data Logger", 
                style={
                    'textAlign': 'center', 
                    'marginBottom': 20, 
                    'paddingTop': 20,
                    'color': '#00d4ff',
                    'fontFamily': 'Courier New, monospace'
                }),
        
        # Status bar
        html.Div(id='status-bar', style={
            'textAlign': 'center',
            'marginBottom': 20,
            'padding': '10px',
            'backgroundColor': '#222',
            'borderRadius': '5px',
            'marginLeft': '20px',
            'marginRight': '20px'
        }),
        
        html.Div([
            html.Div([
                html.H3(id='duration-display', children="Duration: 0.0s"),
                html.H3(id='data-points-display', children="Data Points: 0"),
                html.H3(f"Sample Rate: {logRate} Hz"),
            ], style={
                'display': 'flex', 
                'justifyContent': 'space-around', 
                'marginBottom': 30, 
                'flexWrap': 'wrap',
                'color': '#e0e0e0',
                'fontFamily': 'Courier New, monospace'
            }),
            
            # Live graph - shows last N seconds
            dcc.Graph(
                id='live-pressure-graph', 
                style={'height': '700px', 'marginBottom': 20}
            ),
            
            # Mode selector - only for live mode
            html.Div(id='view-mode-container', children=[
                html.Label("View Mode: ", style={'color': '#e0e0e0', 'fontSize': '16px', 'marginRight': '15px'}),
                dcc.RadioItems(
                    id='view-mode',
                    options=[
                        {'label': ' Last 30 seconds', 'value': 'window'},
                        {'label': ' All data', 'value': 'all'},
                    ],
                    value='window',
                    inline=True,
                    style={'color': '#e0e0e0', 'fontSize': '16px'}
                ),
            ], style={'marginTop': 20, 'marginBottom': 20, 'paddingRight': 20, 'paddingLeft': 20}),
            
        ], style={'padding': '20px', 'margin': 'auto'}),
    ]
)

# Callback to update graph and stats in real-time
@app.callback(
    [Output('live-pressure-graph', 'figure'),
     Output('duration-display', 'children'),
     Output('data-points-display', 'children'),
     Output('status-bar', 'children'),
     Output('elapsed-time-store', 'data'),
     Output('app-title', 'children'),
     Output('view-mode-container', 'style')],
    Input('live-update-interval', 'n_intervals'),
    State('view-mode', 'value')
)
def update_live_graph(n, view_mode):
    with data_lock:
        current_data = list(data_buffer)
    
    # Determine current mode
    current_mode = data_mode or "live"
    
    # Set title and hide view-mode for file mode
    if current_mode == "file":
        title = "File Data Viewer"
        view_mode = 'all'  # Force all data display for files
        view_mode_style = {'display': 'none'}  # Hide the view mode selector
    else:
        title = "Live Pressure Data Logger"
        view_mode_style = {'marginTop': 20, 'marginBottom': 20, 'paddingRight': 20, 'paddingLeft': 20}
    
    print(f"[DEBUG] update_graph called; buffer size={len(current_data)}, mode={current_mode}")
    if current_data:
        print(f"[DEBUG] sample values: {current_data[-5:]}" if len(current_data)>5 else f"[DEBUG] sample values: {current_data}")
    
    # if connection lost and we still have data, force full view (for live mode only)
    if current_mode == "live" and not is_recording and current_data:
        view_mode = 'all'
        stop_recording()
    
    if not current_data:
        # Show empty graph while waiting for data
        fig = go.Figure()
        fig.update_layout(
            title='Waiting for data...',
            xaxis_title='Time (seconds)',
            yaxis_title='Pressure (Pa)',
            yaxis=dict(range=[0, 120000]),  # Generous default range
            template='plotly_dark',
            height=600,
            font=dict(family="Courier New", size=12),
        )
        return fig, "Duration: 0.0s", "Data Points: 0", "Status: Waiting for data...", 0, title, view_mode_style
    
    # Calculate elapsed time
    if start_time:
        if current_mode == "file":
            # For file mode, use total duration based on data points
            elapsed = len(current_data) / logRate
        else:
            # For live mode, use actual elapsed time
            elapsed = time.time() - start_time
    else:
        elapsed = 0
    
    # Prepare data based on view mode
    num_points = len(current_data)
    
    if view_mode == 'window':
        # Show last 30 seconds worth of data
        window_size = int(logRate * 30)  # 150 points at 5Hz
        start_idx = max(0, num_points - window_size)
        display_data = current_data[start_idx:]
        
        # Adjust time axis to show elapsed time
        time_axis = [(elapsed - (num_points - i - 1) / logRate) for i in range(start_idx, num_points)]
    else:
        # Show all data
        display_data = current_data
        time_axis = [i / logRate for i in range(num_points)]
    
    # Calculate generous y-axis range for smoother appearance
    if display_data:
        data_min = min(display_data)
        data_max = max(display_data)
        # Add 15% padding on each side for smoother appearance
        range_padding = (data_max - data_min) * 1.2
        y_min = max(0, data_min - range_padding)  # Don't go below 0 for pressure
        y_max = data_max + range_padding
    else:
        y_min, y_max = 0, 100000  # Default range when no data
    
    # Create figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=time_axis,
        y=display_data,
        mode='lines+markers',
        name='Pressure',
        hovertemplate='<b>Time:</b> %{x:.2f}s<br><b>Pressure:</b> %{y:.2f} Pa<extra></extra>',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=4)
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='Time (seconds)',
        yaxis_title='Pressure (Pa)',
        yaxis=dict(range=[y_min, y_max]),  # Generous range with padding
        hovermode='x unified',
        template='plotly_dark',
        height=600,
        font=dict(family="Courier New", size=12),
        title_font=dict(family="Arial Black", size=24)
    )
    
    # Update statistics
    duration_text = f"Duration: {elapsed:.1f}s"
    points_text = f"Data Points: {num_points}"
    
    if current_mode == "file":
        status_text = f"Status: {connection_status} | File: {loaded_file_path.split('/')[-1] if loaded_file_path else 'Unknown'} | Timestamp: {datetime.now().strftime('%H:%M:%S')}"
    else:
        if not is_recording and connection_status != 'Connected':
            status_text = f"Status: {connection_status} (disconnected) | Displaying full graph | Timestamp: {datetime.now().strftime('%H:%M:%S')}"
        else:
            status_text = f"Status: {connection_status} | Recording: {'Yes' if is_recording else 'No'} | Timestamp: {datetime.now().strftime('%H:%M:%S')}"
    
    return fig, duration_text, points_text, status_text, elapsed, title, view_mode_style

def stop_recording():
    """Stop data collection (called on shutdown)."""
    global is_recording
    is_recording = False

if __name__ == '__main__':
    print("Starting Pressure Data Logger...")
    
    # Show startup dialog to select mode
    # show_startup_dialog()

    # data_mode = "live" # Forcing live mode, I really don't like how the dialog function was implemented so for now I'll leave it like this
    mode_selection_dialog()

    if data_mode == "live":
        print("\nData Source: REAL ARDUINO (LIVE)")
        print("Ensure the Arduino is connected and the correct COM port is specified.")
    elif data_mode == "file":
        print(f"\nData Source: FILE")
        print(f"Loaded file: {loaded_file_path}")
    elif data_mode == "wifi":
        print("\nData Source: REAL ARDUINO (WIFI)")
        print("Ensure the Arduino is connected to the same network and the correct IP/port are specified.")
    # Start background data collection
    start_data_collection()
    
    print(f"\nStarting Dash server...")
    print(f"Open your browser to http://127.0.0.1:8050")
    print("Press Ctrl+C to stop.\n")
    
    try:
        # Disable debug mode/auto-reloader so the data thread runs in the same process
        app.run(debug=False, port=8050)
    except KeyboardInterrupt:
        stop_recording()
        print("\nShutting down...")