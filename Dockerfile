FROM python:3.8-slim

WORKDIR /batfish-wrapper
COPY . /batfish-wrapper
RUN pip install --no-cache-dir -r requirements.txt
ENTRYPOINT ["python3", "app.py"]
