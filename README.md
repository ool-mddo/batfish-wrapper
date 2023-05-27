# batfish-wrapper

Batfish wrapper for MDDO Project

## Setup

Install required packages

```shell
pip3 install -r requirements_prod.txt
```

## Run batfish-wrapper

```shell
python3 src/app.py
```

It will up at `http://localhost:5000/`

## Environment variables

* `BATFISH_HOST`: specify batfish service (hostname)
* `MDDO_CONFIGS_DIR`: batfish snapshot directory (default: `./configs`)
* `MDDO_QUERIES_DIR`: query result directory (default: `./queries`)

## REST API

see. [app.py](./src/app.py)

Parameters in examples:
* network name : `pushed_configs`
* snapshot name: `mddo_network`

### Get network and snapshots in batfish

Get all networks and snapshots
* GET `/batfish/snapshots`

```shell
curl -X GET http://localhost:5000/batfish/snapshots
```

Get networks
* GET `/batfish/networks`

```shell
curl -X GET http://localhost:5000/batfish/networks
```

Get snapshots in a network
* GET `/batfish/<network>/snapshots`
  * `simulated`: [optional] returns all logical (simulated) snapshots defined in the network
    even if these snapshots are not registered in batfish. (default: false)

```shell
curl -X GET http://localhost:5000/batfish/pushed_configs/snapshots
curl -X GET http://localhost:5000/batfish/pushed_configs/snapshots?simulated=true
```

Get nodes in a snapshot
* GET `/batfish/<network>/<snapshot>/nodes`

```shell
curl -X GET http://localhost:5000/batfish/pushed_configs/mddo_network/nodes
```

Get interfaces in a node
* GET `/batfish/<network>/<snapshot>/<node>/interfaces`

```shell
curl -X GET http://localhost:5000/batfish/pushed_configs/mddo_network/regiona-svr01/interfaces
```

Get interfaces in a snapshots
* GET `/batfish/<network>/<snapshot>/interfaces`

```shell
curl -X GET http://localhost:5000/batfish/pushed_configs/mddo_network/interfaces
```

### Query traceroute for all snapshots in a network

L3 Reachability (traceroute) simulation
* GET `/batfish/<network>/<snapshot>/<source-node>/traceroute`
  * `interface`: source interface
  * `destination`: destination IP address

```shell
curl -X GET "http://localhost:5000/batfish/pushed_configs/mddo_network/regiona-svr01/traceroute?interface=enp1s4&destination=172.31.10.1"
```

### Operate logical (linkdown) snapshot pattern

Make snapshot patterns
* POST `/configs/<network>/<snapshot>/snapshot_patterns`
  * `node`: [optional] draw-off (deactivate) target node
  * `interface_regexp`: [optional] draw-off (deactivate) interface name (regexp match)

```shell
# without draw-off
curl -X POST -H "Content-Type: application/json" -d '{}'\
  http://localhost:5000/configs/pushed_configs/mddo_network/snapshot_patterns
# draw-off regiona-pe01[ge-0/0/0]
curl -X POST -H "Content-Type: application/json" \
  -d '{"node": "regiona-pe01", "interface_regexp": "ge-0/0/0"}' \
  http://localhost:5000/configs/pushed_configs/mddo_network/snapshot_patterns
```

CLI
```shell
python3 src/cli_make_snapshot_patterns.py -n pushed_configs -s mddo_network -d regiona-pe01 -l "ge-0/0/0"
```

Fetch snapshot patterns
* GET `/configs/<network>/<snapshot>/snapshot_patterns`

```shell
curl http://localhost:5000/configs/pushed_configs/mddo_network/snapshot_patterns
```

Remove snapshot patterns
* DELETE `/configs/<network>/<snapshot>/snapshot_patterns`

```shell
curl -X DELETE http://localhost:5000/configs/pushed_configs/mddo_network/snapshot_patterns
```

### Exec batfish queries and save these result as csv files (local files)

Make query data
* POST `/queries/<network>` (for all snapshots in the network)
* POST `/queries/<network>/<snapshot>` (for a snapshot)

```shell
# all snapshots
curl -X POST -H "Content-Type: application/json" -d '{}'\
  http://localhost:5000/queries/pushed_configs
# single snapshot
curl -X POST -H "Content-Type: application/json" -d '{}'\
  http://localhost:5000/queries/pushed_configs/mddo_network
```

CLI
* `-n`/`--network`: target network (query for all snapshots in the network without `-s`)
* `-s`/`--snapshot`: [optional] target snapshot (query for single snapshot)

```shell
# all snapshots
python3 src/cli_exec_queries.py -n pushed_configs
# single snapshot
python3 src/cli_exec_queries.py -n pushed_configs -s mddo_network
```

Delete query data
* DELETE `/queries/<network>` (for all snapshots in the network)

```shell
curl -XX DELETE http://localhost:5000/queries/pushed_configs
```

### Register snapshot into batfish (for testing/debugging)

Register snapshot
* POST `/batfish/<network>/<snapshot>/register`
  * `overwrite`: [optional] Overwrite (reload) snapshot

```shell
curl -X POST -H "Content-Type: application/json" -d {} \
  http://localhost:5000/batfish/pushed_configs/mddo_network/register
# if overwrite (reload)
curl -X POST -H "Content-Type: application/json" -d '{"overwrite": true}'\
  http://localhost:5000/batfish/pushed_configs/mddo_network/register
```

### Operate configs git repository

Change current branch
* POST `/configs/<network>/branch`
  * `name` : [optional] branch name (default "main")

```shell
curl -X POST -H "Content-Type: application/json" -d '{"name": "202202demo"}' \
  http://localhost:5000/configs/pushed_configs/branch
```

Fetch current branch
* GET `/configs/<network>/branch`

```shell
curl http://localhost:5000/configs/pushed_configs/branch
```

## Development

### Setup

```shell
pip3 install -r requirements_dev.txt
```

### Format code

```shell
black src/*.py src/**/*.py
```

### Lint

```shell
flake8 --statistics --config .config/flake8 src/
pylint --rcfile .config/pylintrc src/*.py src/**/*.py
```

### Documents

```shell
mkdocs serve
```
and access `http://localhost:8000`
