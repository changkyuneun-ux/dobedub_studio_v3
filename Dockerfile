FROM python:3.12-slim

ENV HOST=0.0.0.0 \
    PORT=8787 \
    PYTHONUNBUFFERED=1 \
    WORKFLOWS_DIR=/app/workflows \
    STUDIO_DATA_DIR=/app/data \
    OUTPUTS_DIR=/app/data/outputs

WORKDIR /app

COPY . .

RUN mkdir -p /app/data/uploads /app/data/outputs /app/data/reports

EXPOSE 8787

CMD ["python", "server.py"]
