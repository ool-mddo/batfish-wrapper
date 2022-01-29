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

### Get network and snapshots in batfish

Get networks
```shell
curl -X GET http://localhost:5000/api/networks
```

Get snapshots in a network
```shell
curl -X GET http://localhost:5000/api/network/pushed_configs/snapshots
```

### Query traceroute for all snapshots in a network
* url:
  * `/api/nodes/<source-node>/traceroute`
* get parameter:
  * interface: source interface
  * destination: destination IP address
  * network: network name
```shell
curl -X GET "http://localhost:5000/api/nodes/regiona-svr01/traceroute?interface=enp1s4&destination=172.31.10.1&network=pushed_configs"
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
  -d '{"input_snapshot_base": "configs/pushed_configs", "network": "pushed_configs"}' \
  http://localhost:5000/api/register_snapshot
```
CLI
```shell
python3 cli/register_snapshots.py -i configs/pushed_configs -n pushed_configs
```

### Exec batfish queries and save these result as csv files (local files)
REST
```shell
curl -X POST -H "Content-Type: application/json" \
  -d '{"network": "pushed_configs"}' \
  http://localhost:5000/api/queries
```
CLI
```shell
python3 cli/exec_queries.py -n pushed_configs
```

## CLI frontend

Scripts in [cli directory](./cli) is CLI frontend for batfish.

## Development

### Format code

```shell
black *.py
```
