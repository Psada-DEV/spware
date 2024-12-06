

from flask import Flask, Response, render_template_string
import cv2
import mss
import numpy as np
import subprocess
import platform
import time
import requests

app = Flask(__name__)

# Fonction pour démarrer Ngrok
def run_ngrok():
    system = platform.system().lower()
    if system == 'windows':
        ngrok_path = 'Z-video\\ngrok.exe'
    else:
        ngrok_path = 'ngrok'
    
    subprocess.Popen([ngrok_path, 'http', '5000'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def get_ngrok_url():
    time.sleep(3)  # Attendre un peu le démarrage de Ngrok
    url = "http://127.0.0.1:4040/api/tunnels"
    response = requests.get(url)
    public_url = response.json()['tunnels'][0]['public_url']
    return public_url

# Fonction pour générer le flux vidéo webcam
def generate_frames():
    camera = cv2.VideoCapture(0)
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# Fonction pour générer le flux de l'écran
def generate_screen_frames():
    with mss.mss() as sct:
        while True:
            screen = sct.grab(sct.monitors[0])
            frame = np.array(screen)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# Route pour la page d'accueil avec boutons
@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Video Stream</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; }
            button { margin: 10px; padding: 10px 20px; font-size: 16px; }
            #stream { display: none; }
        </style>
    </head>
    <body>
        <h1>Video Stream</h1>
        <button onclick="showStream('webcam')">Webcam Stream</button>
        <button onclick="showStream('screen')">Screen Stream</button>
        <div id="stream">
            <img id="streamImg" width="640" height="480">
        </div>
        <script>
            function showStream(type) {
                const streamDiv = document.getElementById('stream');
                const streamImg = document.getElementById('streamImg');
                streamDiv.style.display = 'block';
                if (type === 'webcam') {
                    streamImg.src = "{{ url_for('video_feed') }}";
                } else if (type === 'screen') {
                    streamImg.src = "{{ url_for('screen_feed') }}";
                }
            }
        </script>
    </body>
    </html>
    """)

# Route pour le flux de la webcam
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Route pour le flux de l'écran
@app.route('/screen_feed')
def screen_feed():
    return Response(generate_screen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print('Démarrage de Ngrok...')
    run_ngrok()
    public_url = get_ngrok_url()
    if public_url:
        print(f"URL publique de Ngrok : {public_url}")
    app.run(host='0.0.0.0', port=5000)
