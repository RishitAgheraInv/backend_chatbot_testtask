# Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY app/ .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir httpx==0.24.1

EXPOSE 8000

CMD ["python", "main.py"]
