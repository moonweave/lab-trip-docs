FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TRIPDOC_HOST=0.0.0.0
ENV TRIPDOC_PORT=8501
ENV TRIPDOC_DATA_DIR=/app/data

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8501
CMD ["python", "-m", "tripdoc"]

