FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --upgrade "msgpack>=1.2.1" "setuptools>=78.1.1"

COPY . .

EXPOSE 5005

CMD ["python", "app.py"]