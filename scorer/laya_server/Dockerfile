# Built only with the `laya` compose profile. Serves a Laya checkpoint: the fine-tuned Inkspect
# one mounted at /models (see scorer/training/README.md), or a Hugging Face repo id.
FROM python:3.12-slim

# cpu (small image) or a CUDA wheel index such as cu128 (set by compose.gpu.yaml)
ARG TORCH_INDEX=cpu
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/cache/huggingface
WORKDIR /app
RUN pip install torch --index-url https://download.pytorch.org/whl/${TORCH_INDEX}
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY server.py ./
RUN useradd --create-home --uid 10002 laya && mkdir -p /cache/huggingface && chown laya /cache/huggingface
USER laya

EXPOSE 8100
HEALTHCHECK --interval=10s --timeout=5s --start-period=180s --retries=30 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8100/health', timeout=4).status == 200 else 1)"
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8100"]
