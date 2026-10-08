FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
COPY sql/ sql/
CMD ["sh", "-c", "python src/generate_sources.py && python src/audit.py && python src/load_db.py"]