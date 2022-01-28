# batfish-wrapper

Batfish wrapper for MDDO Project

## Setup

Install required packages

```shell
pip3 install -r requirements.txt
```

## Run batfish-wrapper

```shell
python3 app.py
```

It will up at `http;//localhost:5000/`

## with Batfish

Use `BATFISH_HOST` environment variable to specify batfish service.

## REST API

see. [app.py](./app.py)

## CLI frontend

Scripts in [cli directory](./cli) is CLI frontend for batfish.
Original scripts are in [netomox-exp/configs](https://github.com/ool-mddo/netomox-exp/tree/develop/configs) directory.
But it will be changed to use scripts in this repository via REST api...

## Development

Format code.

```shell
black *.py
```
