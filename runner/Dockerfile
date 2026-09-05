FROM python:3.13-slim
WORKDIR /app
COPY worker.py /app/worker.py
USER 65534:65534
ENTRYPOINT ["python", "-I", "-B", "/app/worker.py"]
