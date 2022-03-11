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

It will up at `http://localhost:5000/`

## with Batfish

Use `BATFISH_HOST` environment variable to specify batfish service.

## REST API

see. [app.py](./app.py)

### Get network and snapshots in batfish

Get networks
```shell
curl -X GET http://localhost:5000/api/networks
```

Get snapshots in a network
```shell
curl -X GET http://localhost:5000/api/networks/pushed_configs/snapshots
```

Get nodes in a snapshot
```shell
curl -X GET http://localhost:5000/api/networks/pushed_configs/snapshots/mddo_network/nodes
```

Get interfaces in a node
```shell
curl -X GET http://localhost:5000/api/networks/pushed_configs/snapshots/mddo_network/nodes/regiona-svr01/interfaces
```

Get interfaces in a snapshots
```shell
curl -X GET http://localhost:5000/api/networks/pushed_configs/snapshots/mddo_network/interfaces
```

### Query traceroute for all snapshots in a network
* url:
  * `/api/networks/<network>/snapshots/<snapshot>/nodes/<source-node>/traceroute`
* get parameter:
  * interface: source interface
  * destination: destination IP address
```shell
curl -X GET "http://localhost:5000/api/networks/pushed_configs/snapshots/mddo_network/nodes/regiona-svr01/traceroute?interface=enp1s4&destination=172.31.10.1"
```

### Make linkdown snapshots (local file)
REST
```shell
curl -X POST -H "Content-Type: application/json" \
  -d '{"input_snapshot_base": "configs/pushed_configs", "output_snapshot_base": "configs/pushed_configs_drawoff", "node": "regiona-svr02"}' \
  http://localhost:5000/api/linkdown_snapshots
```
CLI
```shell
python3 cli/make_linkdown_snapshots.py -i configs/pushed_configs -o configs/pushed_configs_drawoff -n regiona-svr02
```

### Register local snapshots to batfish
REST
```shell
curl -X POST -H "Content-Type: application/json" \
  -d '{"input_snapshot_base": "/mddo/configs/pushed_configs"}' \
  http://localhost:5000/api/networks/pushed_configs
```
CLI
```shell
python3 cli/register_snapshots.py -i configs/pushed_configs -n pushed_configs
```

### Exec batfish queries and save these result as csv files (local files)
REST
```shell
curl -X POST -H "Content-Type: application/json" \
  -d '{"configs_dir": "/mddo/configs", "models_dir": "/mddo/models"}' \
  http://localhost:5000/api/networks/pushed_configs/queries
```
CLI
```shell
python3 cli/exec_queries.py -n pushed_configs -c /mddo/configs -m /mddo/models
```

## CLI frontend

Scripts in [cli directory](./cli) is CLI frontend for batfish.

## Development

### Format code

```shell
black *.py
```
