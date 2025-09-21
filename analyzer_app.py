# Em analyzer_app.py

import pandas as pd
import streamlit as st
import io

# --- Função de Processamento de Dados (sem alterações) ---
def processar_dados(df_abertas, df_relatorio):
    # ... (copie a função processar_dados do seu script original aqui, sem alterá-la)
    """
    Compara duas planilhas para encontrar SVOs pendentes.
    Retorna um DataFrame com as SVOs pendentes e a contagem total.
    """
    df_abertas = df_abertas[
        df_abertas['SVO'].notna() & df_abertas['SVO'].str.startswith('SVO-')
    ].copy()
    df_relatorio = df_relatorio[
        df_relatorio['SVO'].notna() & df_relatorio['SVO'].str.startswith('SVO-')
    ].copy()
    colunas_interesse = ['SVO', 'Status da OS', 'Agendado para', 'Cidade Consumidor']
    for col in colunas_interesse:
        if col not in df_abertas.columns:
            st.error(f"Erro: A coluna '{col}' não foi encontrada na planilha de SVOs Abertas.")
            return pd.DataFrame(), 0
    svos_pendentes = df_abertas[
        ~df_abertas['SVO'].isin(df_relatorio['SVO'])
    ][colunas_interesse].copy()
    quantidade_svos = len(svos_pendentes)
    if not svos_pendentes.empty:
        status_order = svos_pendentes['Status da OS'].unique()
        svos_pendentes['Status da OS'] = pd.Categorical(svos_pendentes['Status da OS'], categories=status_order, ordered=True)
        svos_pendentes = svos_pendentes.sort_values('Status da OS')
        svos_pendentes['Agendado para'] = pd.to_datetime(svos_pendentes['Agendado para'], errors='coerce').dt.strftime('%d/%m/%Y')
        svos_pendentes['Agendado para'] = svos_pendentes['Agendado para'].fillna('Sem Data')
    return svos_pendentes, quantidade_svos


# --- Função Principal que Desenha a Interface ---
def run_analyzer_app():
    st.title("🔎 Analisador de SVOs Pendentes")
    st.markdown("Faça o upload das planilhas para identificar as Ordens de Serviço que precisam de tratamento.")

    st.warning("""
    **ATENÇÃO:** Para o melhor funcionamento da ferramenta:
    - Valide se a planilha de **Origem** e a planilha de **Relatório** são da mesma cidade.
    - Ambas as planilhas devem conter uma coluna chamada **'SVO'**.
    """)

    col1, col2 = st.columns(2)
    with col1:
        origem_file = st.file_uploader("1. Planilha de SVOs Abertas (Origem)", type=['xlsx'])
    with col2:
        modelo_file = st.file_uploader("2. Planilha de Relatório (Modelo)", type=['xlsx'])

    if st.button("Analisar Planilhas", type="primary"):
        if origem_file is not None and modelo_file is not None:
            with st.spinner('Processando os dados... Por favor, aguarde.'):
                planilha_abertas = pd.read_excel(origem_file)
                planilha_relatorio = pd.read_excel(modelo_file)
                svos_pendentes, quantidade_svos = processar_dados(planilha_abertas, planilha_relatorio)

            st.success("Análise concluída!")
            if quantidade_svos > 0:
                st.metric(label="Total de SVOs que precisam de tratamento", value=quantidade_svos)
                
                @st.cache_data
                def convert_df_to_csv(df):
                    return df.to_csv(index=False).encode('utf-8')

                csv = convert_df_to_csv(svos_pendentes)
                st.download_button(
                   label="📥 Baixar resultado como CSV",
                   data=csv,
                   file_name='svos_pendentes.csv',
                   mime='text/csv',
                )
                
                st.markdown("---")
                for status, group in svos_pendentes.groupby('Status da OS', observed=True):
                    with st.expander(f"**{status}** ({len(group)} SVOs)"):
                        st.dataframe(group, use_container_width=True, hide_index=True)
            else:
                st.info("🎉 Nenhuma SVO pendente foi encontrada. Tudo em dia!")
        else:
            st.error("Por favor, faça o upload das duas planilhas para continuar.")