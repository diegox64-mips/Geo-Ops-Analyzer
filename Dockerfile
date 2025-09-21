# Usar uma imagem base com Python
FROM python:3.11-slim

# Definir o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copiar o requirements.txt para o contêiner
COPY requirements.txt .

# Instalar as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todos os arquivos do projeto para o contêiner
COPY . .

# Criar a pasta static/temp_maps se não existir
RUN mkdir -p static/temp_maps

# Expor as portas do Streamlit e Flask
EXPOSE 8501 5000

# Comando para rodar a aplicação
CMD ["sh", "-c", "python mc_webapp.py & streamlit run home.py --server.port=8501 --server.address=0.0.0.0"]