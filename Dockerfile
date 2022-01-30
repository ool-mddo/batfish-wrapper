FROM python:3.8-slim
RUN mkdir -p /batfish-wrapper
WORKDIR /batfish-wrapper
COPY requirements.txt /batfish-wrapper/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /batfish-wrapper/
ENTRYPOINT ["python3", "app.py"]
