# Built only with `docker compose --profile laya`. Downloads the checkpoint on first start
# (mount a volume at /home/laya/.cache/huggingface to keep it).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY server.py ./
RUN useradd --create-home --uid 10002 laya
USER laya

EXPOSE 8100
HEALTHCHECK --interval=15s --timeout=5s --start-period=180s --retries=10 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8100/health', timeout=4).status == 200 else 1)"
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8100"]
