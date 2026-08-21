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
# --proxy-headers + --forwarded-allow-ips: behind the reverse proxy every request arrives
# from the proxy's IP, which would collapse the per-IP login rate limit into one shared
# bucket for all users. Trusting X-Forwarded-For restores real per-user limiting. The
# wildcard is safe because this container publishes no port — only the proxy on the
# internal Docker network can reach it, so the header cannot be forged from outside.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
