from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

# Caminho pra pasta dos mapas (ajuste pra dentro de static)
MAPAS_DIR = os.path.join(os.getcwd(), 'static', 'temp_maps')

@app.route('/')
def home():
    # Lista todos os arquivos HTML na pasta
    mapas = []
    if os.path.exists(MAPAS_DIR):
        mapas = [f for f in os.listdir(MAPAS_DIR) if f.endswith('.html')]
        mapas.sort()  # Organiza por nome
    else:
        print(f"Pasta {MAPAS_DIR} não encontrada. Verifique se ela existe.")
    return render_template('index.html', mapas=mapas)

@app.route('/mapa/<nome_mapa>')
def mostrar_mapa(nome_mapa):
    # DEBUG: Imprime no terminal do Flask o caminho que ele está usando
    print(f"Tentando servir o arquivo: {os.path.join(MAPAS_DIR, nome_mapa)}")
    return send_from_directory(MAPAS_DIR, nome_mapa)

if __name__ == '__main__':
    # Cria a pasta static/temp_maps se não existir
    os.makedirs(MAPAS_DIR, exist_ok=True)
    app.run(debug=True)