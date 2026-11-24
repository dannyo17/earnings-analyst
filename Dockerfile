FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ANONYMIZED_TELEMETRY=False \
    HF_HOME=/home/user/.cache/huggingface

# Hugging Face Spaces runs containers as the user with id 1000
RUN useradd -m -u 1000 user
WORKDIR /app

COPY requirements-deploy.txt .
# CPU-only PyTorch first: the default Linux wheel bundles gigabytes of CUDA libraries
RUN pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements-deploy.txt

USER user

# Download the embedding model at build time so the container starts fast
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# The prebuilt search index changes rarely, so it goes before the code
COPY --chown=user data/chroma ./data/chroma
COPY --chown=user src ./src
COPY --chown=user web ./web

EXPOSE 7860
CMD ["python", "-m", "uvicorn", "--app-dir", "src", "api:app", "--host", "0.0.0.0", "--port", "7860"]