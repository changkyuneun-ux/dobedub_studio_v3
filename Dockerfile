FROM node:24-slim AS frontend-build

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim

ENV HOST=0.0.0.0 \
    PORT=7860 \
    PYTHONUNBUFFERED=1 \
    WORKFLOWS_DIR=/app/workflows \
    STUDIO_DATA_DIR=/app/data \
    OUTPUTS_DIR=/app/data/outputs

WORKDIR /app

COPY . .

COPY --from=frontend-build /frontend/dist /app/frontend/dist

RUN pip install --no-cache-dir -r backend/requirements.txt

RUN mkdir -p /app/data/uploads /app/data/outputs /app/data/reports

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/api/health', timeout=3).read()"]

CMD ["python", "scripts/run_server.py"]
