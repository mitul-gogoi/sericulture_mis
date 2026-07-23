# --- builder ---
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# --- runtime ---
FROM python:3.11-slim
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local
COPY . .

RUN mkdir -p /data/uploads && chown -R appuser:appuser /data/uploads /app

USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH
ENV UPLOAD_ROOT=/data/uploads

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
