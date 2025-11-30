ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-alpine

RUN apk add --no-cache \
    gcc \
    musl-dev \
    mariadb-connector-c-dev

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY exporter.py /app/
RUN chmod +x /app/exporter.py

WORKDIR /app

EXPOSE 9101

CMD ["/app/exporter.py"]
