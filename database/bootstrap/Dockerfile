FROM python:3.11-slim

WORKDIR /workspace
COPY database/bootstrap/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY database/bootstrap/data_quality.py /workspace/database/bootstrap/data_quality.py
COPY database/bootstrap/bootstrap.py database/bootstrap/spatial.py /workspace/database/bootstrap/
COPY database/bootstrap/01_serving_tables.sql /workspace/database/bootstrap/01_serving_tables.sql
COPY analytics /workspace/analytics

CMD ["python", "/workspace/database/bootstrap/bootstrap.py"]
