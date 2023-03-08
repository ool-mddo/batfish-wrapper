FROM python:3.8-slim

RUN mkdir -p /batfish-wrapper
WORKDIR /batfish-wrapper
COPY . /batfish-wrapper/

# install gitops for GitPython
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements_prod.txt
# enable multiple line paste in python REPL (python -i)
RUN echo "set enable-bracketed-paste off" >> ~/.inputrc
ENV PYTHONPATH=/batfish-wrapper/src/bfwrapper
ENTRYPOINT ["/bin/sh", "/batfish-wrapper/entrypoint.sh"]
