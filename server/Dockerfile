# UnloadSystems Remote — server (zero dependinte externe)
FROM python:3.12-slim
WORKDIR /app
COPY unloadsystem/ ./unloadsystem/
COPY run.py ./
ENV US_HOST=0.0.0.0 US_PORT=8000 US_DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8000
CMD ["python", "run.py"]
