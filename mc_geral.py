import pandas as pd
import folium
from datetime import date, datetime, timedelta
from folium.plugins import HeatMapWithTime, MarkerCluster
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import json
import os
import uuid

def filtro_futuro(caminho_do_arquivo):
    print("Iniciando o processo de filtro...")

    try:
        df = pd.read_excel(caminho_do_arquivo)
        print("Planilha lida com sucesso!")
    except FileNotFoundError:
        print(f"Erro: O arquivo '{caminho_do_arquivo}' não foi encontrado.")
        return None

    df['Agendado para'] = pd.to_datetime(df['Agendado para'], errors='coerce')
    print("Coluna 'Agendado para' convertida para o formato de data.")
    hoje = pd.Timestamp(date.today())
    futuro = hoje + timedelta(days=10)
    
    print(f"Filtrando entre {hoje.strftime('%d/%m/%Y')} e {futuro.strftime('%d/%m/%Y')}")
    condicao_inicio = (df['Agendado para'] >= hoje)
    condicao_fim = (df['Agendado para'] <= futuro)
    mascara_final = condicao_inicio & condicao_fim
    
    df_filtrado = df[mascara_final]
    df_final = df_filtrado[['Agendado para', 'Bairro Consumidor', 'Cidade Consumidor', 'SVO']]
    
    print("Filtro aplicado! Veja o resultado:")
    print(df_final.head())
    return df_final

def mapa(dados):
    # Verifica se 'dados' é um DataFrame válido
    if not isinstance(dados, pd.DataFrame):
        print("Erro: Os dados fornecidos não são um DataFrame.")
        return None, None
    
    # Verifica se as colunas necessárias estão presentes
    colunas_necessarias = ['Agendado para', 'Bairro Consumidor', 'Cidade Consumidor', 'SVO']
    if not all(coluna in dados.columns for coluna in colunas_necessarias):
        print("Erro: O DataFrame não contém todas as colunas necessárias.")
        return None, None
    
    # Criar uma cópia do DataFrame para evitar modificações no original
    df_filtrado = dados[['Agendado para', 'Bairro Consumidor', 'Cidade Consumidor', 'SVO']].copy()
    df_filtrado['Agendado para'] = pd.to_datetime(df_filtrado['Agendado para'], errors='coerce')

    # Tratar valores nulos
    df_filtrado = df_filtrado.dropna(subset=['Bairro Consumidor', 'Cidade Consumidor', 'Agendado para'])
    if df_filtrado.empty:
        print("Erro: Nenhum dado válido após remoção de valores nulos.")
        return None, None

    # ==============================================================================
    # ETAPA 1: GEOCODIFICAÇÃO (OBTER COORDENADAS DOS ENDEREÇOS)
    # ==============================================================================
    print("Iniciando a geocodificação dos endereços. Isso pode levar um momento...")

    geolocator = Nominatim(user_agent="gerador_mapa_calor_v1")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, error_wait_seconds=10)

    # Carregar cache de geocodificação, se existir
    try:
        with open('location_cache.json', 'r') as f:
            content = f.read().strip()
            if not content:
                location_cache = {}
            else:
                location_cache = json.loads(content)
    except FileNotFoundError:
        location_cache = {}
    except json.JSONDecodeError:
        print("Erro: O arquivo 'location_cache.json' contém dados inválidos. Inicializando cache vazio.")
        location_cache = {}

    # Criar endereços únicos
    df_filtrado['endereco'] = df_filtrado['Bairro Consumidor'] + ', ' + df_filtrado['Cidade Consumidor'] + ', São Paulo, Brazil'
    enderecos_unicos = df_filtrado['endereco'].unique()

    # Geocodificar apenas endereços únicos
    for address in enderecos_unicos:
        if address not in location_cache:
            try:
                location = geocode(address)
                if location:
                    location_cache[address] = (location.latitude, location.longitude)
                    print(f"Sucesso: {address} -> {location_cache[address]}")
                else:
                    location_cache[address] = (None, None)
                    print(f"Falha: Endereço não encontrado para {address}")
            except Exception as e:
                print(f"Erro de conexão ao buscar {address}: {e}")
                location_cache[address] = (None, None)

    # Salvar cache
    with open('location_cache.json', 'w') as f:
        json.dump(location_cache, f)

    # Mapear coordenadas para o DataFrame
    df_filtrado['latitude'] = df_filtrado['endereco'].map(lambda x: location_cache[x][0])
    df_filtrado['longitude'] = df_filtrado['endereco'].map(lambda x: location_cache[x][1])

    # Remover linhas com coordenadas inválidas
    df_filtrado = df_filtrado.dropna(subset=['latitude', 'longitude'])
    if df_filtrado.empty:
        print("Nenhum endereço pôde ser geocodificado. Encerrando o script.")
        return None, None

    print("\nGeocodificação concluída.\n")

    # ==============================================================================
    # ETAPA 2: AGRUPAR DADOS POR DIA E LOCALIZAÇÃO
    # ==============================================================================
    df_filtrado['Agendado para'] = df_filtrado['Agendado para'].dt.tz_localize(None)
    df_agrupado = df_filtrado.groupby(
        [df_filtrado['Agendado para'].dt.date, 'latitude', 'longitude']
    ).size().reset_index(name='contagem')

    print("\nDados agrupados para o mapa:\n")
    print(df_agrupado.head())

    # ==============================================================================
    # ETAPA 3: PREPARAR OS DADOS PARA O PLUGIN DO FOLIUM
    # ==============================================================================
    dados_para_mapa = []
    datas_unicas = sorted(df_agrupado['Agendado para'].unique())
    for data_unica in datas_unicas:
        df_dia = df_agrupado[df_agrupado['Agendado para'] == data_unica]
        lista_dia = df_dia[['latitude', 'longitude', 'contagem']].values.tolist()
        dados_para_mapa.append(lista_dia)

    indice_tempo = [d.strftime('%d/%m/%Y') for d in datas_unicas]

    # ==============================================================================
    # ETAPA 4: CRIAR E SALVAR O MAPA
    # ==============================================================================
    print("Criando mapa customizado...")

    if not df_filtrado.empty:
        cidade = df_filtrado['Cidade Consumidor'].iloc[0]
    else:
        cidade = "Localidade não definida"

    data_hoje = date.today()
    data_futuro = data_hoje + timedelta(days=10)
    hoje_formatado = data_hoje.strftime('%d/%m/%Y')
    futuro_formatado = data_futuro.strftime('%d/%m/%Y')
    titulo = f"Mapa de Calor Geral | {cidade} | {hoje_formatado} à {futuro_formatado}"

    html_content = f"""
        <div class="map-title-container">
            <h1>{titulo}</h1>
        </div>
    """

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

    mapa_centro = [df_filtrado['latitude'].mean(), df_filtrado['longitude'].mean()]
    mapa_customizado = folium.Map(location=mapa_centro, zoom_start=12, tiles="OpenStreetMap")
    mapa_customizado.get_root().header.add_child(folium.Element(css_style))
    mapa_customizado.get_root().html.add_child(folium.Element(html_content))

    # ==============================================================================
    # ETAPA 5: ADICIONAR TABELA DE RESUMO POR BAIRRO
    # ==============================================================================
    print("Criando tabela de resumo por bairro...")

    contagem_bairros = df_filtrado.groupby('Bairro Consumidor').size().reset_index(name='Quantidade')
    contagem_bairros.columns = ['Bairro', 'Quantidade']
    print(contagem_bairros)

    tabela_html = contagem_bairros.to_html(
        classes="table table-striped table-hover table-condensed table-responsive",
        index=False
    )
    
    titulo_tabela = '<h4>OS por Região (no período)</h4>'
    
    css_tabela = """
    <style>
    .summary-table-container {
        position: fixed; 
        bottom: 80px; 
        left: 20px; 
        width: 250px; 
        max-height: 200px;
        overflow-y: auto;
        background-color: rgba(255, 255, 255, 0.85); 
        z-index: 1001; 
        border: 2px solid grey;
        border-radius: 8px;
        padding: 10px;
        font-family: Arial, sans-serif;
        font-size: 12px;
    }
    .summary-table-container h4 {
        margin-top: 0;
        text-align: center;
        color: #003366;
    }
    .summary-table-container table {
        width: 100%;
    }
    </style>
    """

    html_final_tabela = f"""
    <div class="summary-table-container">
        {titulo_tabela}
        {tabela_html}
    </div>
    """

    mapa_customizado.get_root().header.add_child(folium.Element(css_tabela))
    mapa_customizado.get_root().html.add_child(folium.Element(html_final_tabela))

    heatmap_layer = HeatMapWithTime(
        data=dados_para_mapa,
        index=indice_tempo,
        name="Mapa de Calor por Dia",
        auto_play=False,
        max_opacity=0.4,
        radius=35
    )
    heatmap_layer.add_to(mapa_customizado)

    marker_group = folium.FeatureGroup(name="Agendamentos Individuais (Cluster)")
    marker_cluster = MarkerCluster().add_to(marker_group)

    for idx, row in df_filtrado.iterrows():
        html_popup = f"""
        <b>Bairro:</b> {row['Bairro Consumidor']}<br>
        <b>Cidade:</b> {row['Cidade Consumidor']}<br>
        <b>Agendado para:</b> {row['Agendado para'].strftime('%d/%m/%Y')}
        """
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(html_popup, max_width=250),
            tooltip="Clique para ver detalhes"
        ).add_to(marker_cluster)

    marker_group.add_to(mapa_customizado)
    folium.LayerControl(collapsed=False, position='bottomright').add_to(mapa_customizado)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
    MAPAS_DIR = os.path.join(BASE_DIR, 'static', 'temp_maps')

    os.makedirs(MAPAS_DIR, exist_ok=True)

    nome_arquivo_saida = os.path.join(MAPAS_DIR, f"{cidade}_geral{datetime.now().strftime('%Y%m%d%H%M')}.html")

    mapa_customizado.save(nome_arquivo_saida)

    print(f"\nMapa: '{nome_arquivo_saida}' criado com sucesso!\n")
    return mapa_customizado, nome_arquivo_saida  # Retorna o mapa e o caminho

if __name__ == "__main__":
    baseSVO = r"C:\Users\Data_Analyst\Desktop\Projetos\0.xlsx"
    resultado = filtro_futuro(baseSVO)
    if resultado is not None:
        mapa(resultado)