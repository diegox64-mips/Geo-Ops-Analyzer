import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import folium
from datetime import date
from folium.plugins import HeatMap
import time
import os  # Adicionei isso pra checar se pasta existe

def SVOMaps(arquivo_excel: str, coluna_bairro: str, cidade_estado: str, mapa_html: str, data_filtro: str = None):
    print(f"\n[ + ] Iniciando o processo para {cidade_estado}...")

    # --- 1. Ler e Preparar os Dados ---
    try:
        df = pd.read_excel(arquivo_excel)
        print("Arquivo do Excel lido com sucesso.")
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{arquivo_excel}' não encontrado.")
        return None

    # --- 2. Filtrar os Dados pela Data ---
    df['Agendado para'] = pd.to_datetime(df['Agendado para'], errors='coerce')

    data_filtro_dt = None  # Inicializa como None
    if data_filtro:
        try:
            data_filtro_dt = pd.to_datetime(data_filtro)
            df_filtrado = df[df['Agendado para'].dt.date == data_filtro_dt.date()]
        except ValueError:
            print(f"ERRO: A data '{data_filtro}' não é válida. Use o formato 'YYYY-MM-DD'.")
            return None
    else:
        df_filtrado = df[df['Agendado para'].isna()]

    if df_filtrado.empty:
        print(f"AVISO: Nenhum agendamento encontrado para {data_filtro or 'sem data'} em {cidade_estado}.")
        return None

    print(f"{len(df_filtrado)} agendamentos encontrados para {data_filtro or 'sem data'}.")

    # --- 3. Agregar os Dados dos Bairros (APÓS o filtro) ---
    contagem_bairros = df_filtrado[coluna_bairro].value_counts().reset_index()
    contagem_bairros.columns = ['Bairro Consumidor', 'contagem']
    
    print(f"Dados agregados com sucesso. {len(contagem_bairros)} bairros únicos encontrados para a data.")
    print(contagem_bairros.head())  # Mostra os primeiros bairros

    # --- 4. Geocodificar os Bairros ÚNICOS ---
    print("\nIniciando geocodificação dos bairros...")
    geolocator = Nominatim(user_agent="HeatMap", timeout=10)
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, error_wait_seconds=5)

    contagem_bairros['latitude'] = None
    contagem_bairros['longitude'] = None

    for index, row in contagem_bairros.iterrows():
        query = f"{row['Bairro Consumidor']}, {cidade_estado}"
        print(f"Buscando coordenadas para: '{query}'")
        
        try:
            location = geocode(query)
            if location:
                contagem_bairros.loc[index, 'latitude'] = location.latitude
                contagem_bairros.loc[index, 'longitude'] = location.longitude
                print(f"[ + ] Encontrado: ({location.latitude:.4f}, {location.longitude:.4f})")
            else:
                print(" -> Localização não encontrada.")
        except Exception as e:
            print(f" -> ERRO de conexão ao buscar '{query}'. Pulando.")

    contagem_bairros.dropna(subset=['latitude', 'longitude'], inplace=True)
    
    # --- 5. Criar e Salvar o Mapa de Calor ---
    print("\nCriando o mapa de calor...")
    
    if contagem_bairros.empty:
        print("ERRO: Nenhum bairro foi geocodificado com sucesso. O mapa não pode ser gerado.")
        return None
        
    mapa_centro = [contagem_bairros['latitude'].mean(), contagem_bairros['longitude'].mean()]
    mapa_calor = folium.Map(location=mapa_centro, zoom_start=12)  # Ajustei o zoom inicial

    # Adiciona o título e a logo (seu código original)
    cidade = cidade_estado.split(',')[0]

    # Antes de criar o título, define data_correta
    if data_filtro_dt is not None:
        data_correta = data_filtro_dt.strftime('%d/%m/%Y')
    else:
        data_correta = "Sem Data"

    # Agora cria o html_content com o título
    html_content = f"""
    <div class="map-title-container">
        <h1>Mapa de Calor | {cidade} | {data_correta}</h1>
    </div>
    """
    # Adicionei o CSS aqui para ficar mais organizado
    css_style = """
    <style>
      .map-title-container {
          position: fixed; top: 0; left: 0; width: 100%; height: 60px;
          background-color: #ffffff; display: flex; align-items: center;
          padding: 0 20px; border-bottom: 2px solid #f0f0f0; z-index: 1000; box-sizing: border-box;
      }
      .map-title-container h1 {
          position: absolute; left: 50%; transform: translateX(-50%);
          font-family: Arial, sans-serif; color: #003366; font-size: 20px; margin: 0;
      }
      .map-title-container img {
          position: absolute; right: 20px;
          max-height: 40px; width: auto;
      }
    </style>
    """
    mapa_calor.get_root().header.add_child(folium.Element(css_style))
    mapa_calor.get_root().html.add_child(folium.Element(html_content))

    # Adiciona a camada de calor e os marcadores
    dados_heatmap = contagem_bairros[['latitude', 'longitude', 'contagem']].values.tolist()
    HeatMap(dados_heatmap, radius=25, blur=15).add_to(mapa_calor)

    for index, row in contagem_bairros.iterrows():
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            tooltip=f"{row['Bairro Consumidor']}: {row['contagem']} O.S.",
            icon=None
        ).add_to(mapa_calor)

    # --- 6. Salvar o Mapa ---
    mapa_calor.save(mapa_html)
    print(f"\nProcesso concluído! Mapa de calor salvo em '{mapa_html}'")
    return mapa_html  # Retorna o caminho do mapa pra mostrar no Streamlit

# Função nova: pra processar múltiplas cidades e arquivos
def gerar_mapas_multiplos(arquivos_excels, coluna_bairro, cidades, data_filtro):
    mapas_gerados = []
    num_arquivos = len(arquivos_excels)
    num_cidades = len(cidades)
    
    if not os.path.exists('temp_maps'):
        os.makedirs('temp_maps')
    
    for i, cidade in enumerate(cidades):
        # Define o sufixo do nome do arquivo com base em data_filtro
        if data_filtro:
            try:
                data_filtro_dt = pd.to_datetime(data_filtro)
                data_suffix = data_filtro_dt.strftime('%Y%m%d')
            except ValueError:
                print(f"ERRO: A data '{data_filtro}' não é válida. Usando 'sem_data'.")
                data_suffix = "sem_data"
        else:
            data_suffix = "sem_data"
        
        arquivo = arquivos_excels[min(i, num_arquivos - 1)]
        cidade_nome = cidade.replace(", SP", "")
        nome_mapa = os.path.join('static', 'temp_maps', f'{cidade_nome}_{data_suffix}.html')
        resultado = SVOMaps(arquivo, coluna_bairro, cidade, nome_mapa, data_filtro)
        if resultado:
            mapas_gerados.append((cidade_nome, nome_mapa))
        time.sleep(5)
    
    # Gera o HTML combinado
    if mapas_gerados:
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Mapas de Calor</title>
    <style>
        h1 {
            text-align: center;
            font-family: Arial, sans-serif;
            color: #003366;
        }
        iframe {
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
"""
        for cidade_nome, mapa_path in mapas_gerados:
            mapa_nome = os.path.basename(mapa_path)
            html_content += f"""
    <h1>Mapa de {cidade_nome}</h1>
    <iframe src="{mapa_nome}" width="100%" height="500px" style="border:none;"></iframe>
"""
        html_content += """
</body>
</html>
"""
        combined_html_path = 'temp_maps/mmaps.html'
        with open(combined_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        mapas_gerados.append(('Combinado', combined_html_path))
    
    return [(cidade, caminho_mapa) for cidade, caminho_mapa in mapas_gerados]