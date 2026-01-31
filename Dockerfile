FROM python:3.9-slim

WORKDIR /app

# Copia requirements primeiro
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia a aplicação
COPY . .

# Cria diretórios
RUN mkdir -p data static/uploads logs

EXPOSE 5000

CMD ["python", "app.py"]
