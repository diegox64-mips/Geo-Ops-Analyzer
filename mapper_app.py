# Em mapper_app.py

import streamlit as st
import pandas as pd
from datetime import datetime
import os
import shutil
from mc_simple import SVOMaps
from mc_geral import filtro_futuro, mapa
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# --- Função Principal que Desenha a Interface ---
def run_mapper_app():
    if 'mapas_gerados' not in st.session_state:
        st.session_state.mapas_gerados = []

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title('Gerador de Mapas de Calor')

    st.header('Faça o upload de até dois arquivos ".xlsx"')
    uploaded_files = st.file_uploader(
        "Clique em 'Browse Files' e escolha até dois arquivos XLSX:",
        type="xlsx",
        accept_multiple_files=True
    )

    selected_date = st.date_input(
        "Filtrar por data específica (Passe o mouse em '?'):",
        value=None,
        help="""Escolha uma data para gerar um mapa para aquele dia. Se deixar em branco, o mapa será gerado para as ordens SEM data agendada."""
    )

    st.markdown("---")

    if st.button("Gerar Mapas de Calor!", type="primary"):
        # ... (copie todo o conteúdo do botão "Gerar Mapas de Calor!" para cá, sem alterações)
        if not uploaded_files:
            st.error("Ei, você precisa fazer upload de pelo menos um arquivo primeiro!")
            st.stop()
        
        if len(uploaded_files) > 2:
            st.error("No máximo dois arquivos, por favor!")
            st.stop()
        
        if selected_date is None:
            st.warning("Nenhuma data foi selecionada. Gerando mapas para SVOs sem data definida!")
            data_filtro = None
        else:
            data_filtro = selected_date.strftime('%Y-%m-%d')
            data_br = selected_date.strftime('%d/%m/%Y')
            st.success(f"A data selecionada foi: {data_br}. Gerando mapas para esta data.")
        
        temp_dir = os.path.join(os.getcwd(), "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        maps_dir = os.path.join(os.getcwd(), "static", "temp_maps")
        os.makedirs(maps_dir, exist_ok=True)
            
        caminhos_arquivos = []
        for uploaded_file in uploaded_files:
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_path, "wb") as f:
                shutil.copyfileobj(uploaded_file, f)
            caminhos_arquivos.append(temp_path)
            st.success(f"Arquivo Processado: '{uploaded_file.name}'")
        
        mapas_gerados = []
        coluna_bairro = 'Bairro Consumidor'
        
        with st.spinner("Gerando mapas, isso pode levar alguns instantes..."):
            for caminho_arquivo in caminhos_arquivos:
                try:
                    df_temp = pd.read_excel(caminho_arquivo)
                    if 'Cidade Consumidor' in df_temp.columns and not df_temp['Cidade Consumidor'].empty:
                        cidade_nome = df_temp['Cidade Consumidor'].dropna().unique()[0]
                        cidade_estado = f"{cidade_nome}, SP"
                        data_suffix = pd.to_datetime(data_filtro).strftime('%Y%m%d') if data_filtro else "sem_data"
                        nome_mapa = f'static/temp_maps/{cidade_nome.replace(" ", "_")}_{data_suffix}.html'
                        st.info(f"Gerando mapa para {cidade_nome}...")
                        resultado = SVOMaps(arquivo_excel=caminho_arquivo, coluna_bairro=coluna_bairro, cidade_estado=cidade_estado, mapa_html=nome_mapa, data_filtro=data_filtro)
                        if resultado:
                            mapas_gerados.append((cidade_nome, nome_mapa))
                    else:
                        st.warning(f"Não foi possível encontrar a coluna 'Cidade Consumidor' no arquivo {os.path.basename(caminho_arquivo)}.")
                except Exception as e:
                    st.error(f"Ocorreu um erro ao processar o arquivo {os.path.basename(caminho_arquivo)}: {e}")

            for caminho_arquivo in caminhos_arquivos:
                df_filtrado = filtro_futuro(caminho_arquivo)
                if df_filtrado is not None and not df_filtrado.empty:
                    mapa_gerado, nome_arquivo_mapa = mapa(df_filtrado)
                    if mapa_gerado:
                        cidade = df_filtrado['Cidade Consumidor'].iloc[0] if not df_filtrado.empty else "Desconhecida"
                        mapas_gerados.append((f"{cidade} (Futuros 10 dias)", nome_arquivo_mapa))
                        st.success(f"Mapa de agendamentos futuros gerado para {cidade}.")
                    
        st.session_state.mapas_gerados = mapas_gerados if mapas_gerados else []

    if st.session_state.mapas_gerados:
        # ... (copie o resto do código da interface aqui)
        st.header("Visualização dos Mapas Gerados")
        for cidade_nome, mapa_path in st.session_state.mapas_gerados:
            mapa_nome_arquivo = os.path.basename(mapa_path)
            flask_url = f"http://localhost:5000/mapa/{mapa_nome_arquivo}"
            st.markdown(f"""<a href="{flask_url}" target="_blank" style="text-decoration: none;"><button style="background-color: #003366; color: white; font-size: 16px; padding: 10px 24px; border-radius: 8px; border: none; cursor: pointer; margin: 5px 0;">Visualizar Mapa: {cidade_nome}</button></a>""", unsafe_allow_html=True)
        if st.button("Limpar Mapas Gerados", type="secondary"):
            st.session_state.mapas_gerados = []
            st.rerun()

    if uploaded_files:
        with st.expander("Mostrar prévia dos arquivos carregados"):
            for uploaded_file in uploaded_files:
                try:
                    df = pd.read_excel(uploaded_file)
                    st.write(f"Prévia do arquivo {uploaded_file.name}:")
                    st.dataframe(df.head())
                except Exception as e:
                    st.error(f"Erro ao ler {uploaded_file.name}: {e}")