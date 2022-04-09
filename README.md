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

## Environment variables

* `BATFISH_HOST`: specify batfish service (hostname)
* `MDDO_CONFIGS_DIR`: batfish snapshot directory (default: `./configs`)
* `MDDO_MODELS_DIR`: query result directory (default: `./models`)

## REST API

see. [app.py](./app.py)

Parameters in examples:
* network name : `pushed_configs`
* snapshot name: `mddo_network`

### Get network and snapshots in batfish

Get all networks and snapshots
```shell
curl -X GET http://localhost:5000/api/snapshots
```

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
REST
* GET `/api/networks/<network>/snapshots/<snapshot>/nodes/<source-node>/traceroute`
  * `interface`: source interface
  * `destination`: destination IP address

```shell
curl -X GET "http://localhost:5000/api/networks/pushed_configs/snapshots/mddo_network/nodes/regiona-svr01/traceroute?interface=enp1s4&destination=172.31.10.1"
```

### Make simulated snapshot patterns
REST
* POST `/api/networks/<network>/snapshots/<snapshot>/patterns`
  * `node`: [optional] draw-off (deactivate) target node
  * `link_regesp`: [optional] draw-off (deactivate) interface name (regexp match)

```shell
# without draw-off
curl -X POST -H "Content-Type: application/json" -d '{}'\
  http://localhost:5000/api/networks/pushed_configs/snapshots/mddo_network/patterns
# draw-off regiona-pe01[ge-0/0/0]
curl -X POST -H "Content-Type: application/json" \
  -d '{"node": "regiona-pe01", "link_regexp": "ge-0/0/0"}' \
  http://localhost:5000/api/networks/pushed_configs/snapshots/mddo_network/patterns
```

CLI
```shell
python3 cli/cli/make_snapshot_patterns.py -n pushed_configs -s mddo_network -d regiona-pe01 -l "ge-0/0/0"
```

### Exec batfish queries and save these result as csv files (local files)
REST
* POST `/api/networks/<network>/queries` (for all snapshots in the network)
* POST `/api/networks/<network>/snapshots/<snapshot>/queries` (for a snapshot)

```shell
# all snapshots
curl -X POST -H "Content-Type: application/json" -d '{}'\
  http://localhost:5000/api/networks/pushed_configs/queries
# single snapshot
curl -X POST -H "Content-Type: application/json" -d '{}'\
  http://localhost:5000/api/networks/pushed_configs/snapshots/mddo_network/queries
```

CLI
* `-n`/`--network`: target network (query for all snapshots in the network without `-s`)
* `-s`/`--snapshot`: [optional] target snapshot (query for single snapshot)

```shell
# all snapshots
python3 cli/exec_queries.py -n pushed_configs
# single snapshot
python3 cli/exec_queries.py -n pushed_configs -s mddo_network
```

### Register snapshot into batfish (for testing/debugging)
REST
* POST `/api/networks/<network>/snapshots/<snapshot>/register`
  * `overwrite`: [optional] Overwrite (reload) snapshot

```shell
curl -X PUSH -H "Content-Type: application/json" -d {} \
  http://localhost:5000/api/networks/pushed_configs/snapshots/mddo_network/register
# if overwrite (reload)
curl -X PUSH -H "Content-Type: application/json" -d '{"overwrite": true}'\
  http://localhost:5000/api/networks/pushed_configs/snapshots/mddo_network/register
```

## Development

### Format code

```shell
black *.py
```
