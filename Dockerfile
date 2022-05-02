FROM python:3.8-slim

RUN mkdir -p /batfish-wrapper
WORKDIR /batfish-wrapper
COPY . /batfish-wrapper/

RUN pip install --no-cache-dir -r requirements_prod.txt
# enable multiple line paste in python REPL (python -i)
RUN echo "set enable-bracketed-paste off" >> ~/.inputrc
ENV PYTHONPATH=/batfish-wrapper/src/bfwrapper
ENTRYPOINT ["python3", "src/app.py"]
