# GPU image for building the dataset, fine-tuning and evaluating the Laya coder.
# docker build -t inkspect-laya-train scorer/training   (context: repo root is mounted at run time)
FROM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/cache/huggingface
RUN pip install "laya==0.3.21" "pydantic>=2.13,<3" "httpx>=0.28,<1"
WORKDIR /work
