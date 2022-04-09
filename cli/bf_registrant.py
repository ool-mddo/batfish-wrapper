import os
from pybatfish.datamodel.flow import HeaderConstraints
from bf_registrant_base import BatfishRegistrantBase
from l1_topology_operator import L1TopologyOperator
from typing import List, Dict, Optional, TypedDict

BATFISH_HOST = os.environ.get("BATFISH_HOST", "localhost")
CONFIGS_DIR = os.environ.get("MDDO_CONFIGS_DIR", "./configs")


class SnapshotPatternDict(TypedDict):
    index: int
    lost_edges: List[Dict[str, str]]  # TODO: define edge type
    orig_snapshot_path: str
    orig_snapshot_name: str
    source_snapshot_name: str
    target_snapshot_name: str
    description: str


class BatfishRegistrant(BatfishRegistrantBase):
    def __init__(self, bf_host, mddo_configs_dir):
        super().__init__(bf_host, mddo_configs_dir)

    def bf_node_list(self, network_name, snapshot_name):
        self.bf.set_network(network_name)
        self.bf.set_snapshot(snapshot_name)
        return self.bf.q.nodeProperties().answer().frame()

    def bf_interface_list(self, network_name, snapshot_name):
        self.bf.set_network(network_name)
        self.bf.set_snapshot(snapshot_name)
        return self.bf.q.interfaceProperties().answer().frame()

    def bf_node_interface_list(self, network_name, snapshot_name, node_name):
        self.bf.set_network(network_name)
        self.bf.set_snapshot(snapshot_name)
        return self.bf.q.interfaceProperties(nodes=node_name).answer().frame()

    def l1topology_to_df(self, network, snapshot):
        l1topology_opr = L1TopologyOperator(self.configs_dir, network, self._detect_physical_snapshot_name(snapshot))
        l1topology_edges = l1topology_opr.edges()
        if self._is_physical_snapshot(network, snapshot):
            return l1topology_opr.edges_to_dataframe(l1topology_edges)

        snapshot_pattern = self._find_snapshot_pattern(network, snapshot)
        return l1topology_opr.edges_to_dataframe(
            l1topology_opr.filter_edges(l1topology_edges, snapshot_pattern["lost_edges"])
        )

    def _get_interface_first_ip(self, network: str, snapshot: str, node: str, interface: str):
        """
        get ip address (without CIDR) of node_name and interface
        """
        self.bf.set_network(name=network)
        self.bf.set_snapshot(name=snapshot)
        intf_ip_prefix = (
            self.bf.q.interfaceProperties(nodes=node, interfaces=interface)
            .answer()
            .frame()
            .to_dict()["All_Prefixes"][0][0]
        )
        return intf_ip_prefix[: intf_ip_prefix.find("/")]

    # network
    def get_batfish_networks(self) -> List[str]:
        """
        returns:
        * a list of network names (str)
        """
        return self.bf.list_networks()

    # snapshot
    def get_batfish_snapshots(self, network_name: Optional[str] = None) -> Dict[str, List[str]]:
        """
        params:
        * network_name
        returns: a dict of key: network_name (str) and value: a list of snapshot_names (str)
        """
        ret = {}
        if network_name:
            self.bf.set_network(network_name)
            return {network_name: self.bf.list_snapshots()}
        else:
            for network in self.bf.list_networks():
                for name, snapshots in self.get_batfish_snapshots(network_name=network).items():
                    ret[name] = snapshots
            return ret

    def get_snapshot_patterns(self, network, snapshot):
        if self._is_physical_snapshot(network, snapshot):
            return self._read_snapshot_patterns(network, snapshot)  # all snapshot patterns or [] if not found
        return self._find_snapshot_pattern(network, snapshot)  # single snapshot pattern or None if not found

    # traceroute-query related functions

    def _rec_dict(self, obj):
        """
        translate obj into dict structure recursively
        """
        if isinstance(obj, dict):
            data = {}
            for (k, v) in obj.items():
                data[k] = self._rec_dict(v)
            return data
        elif hasattr(obj, "__iter__") and not isinstance(obj, str):
            return [self._rec_dict(v) for v in obj]
        elif hasattr(obj, "__dict__"):
            return dict(
                [
                    (key, self._rec_dict(value))
                    for key, value in obj.__dict__.items()
                    if not callable(value) and not key.startswith("_")
                ]
            )
        else:
            return obj

    @staticmethod
    def _is_disabled_intf(snapshot_pattern: SnapshotPatternDict, node_name: str, intf_name: str) -> bool:
        """
        check whether the interface is disabled or not in this snapshot
        """
        if snapshot_pattern is None:
            return False

        for lost_edge in snapshot_pattern["lost_edges"]:
            for node_key in ["node1", "node2"]:
                edge = lost_edge[node_key]
                # NOTE: node names in snapshot-info are case-sensitive
                if edge["hostname"].lower() == node_name.lower() and edge["interfaceName"] == intf_name:
                    return True
        return False

    def exec_traceroute_query(self, node_name, intf_name, destination, network, snapshot, logger):
        # app.logger.debug("_traceroute: node=%s intf=%s intf_ip=%s dst=%s nw=%s ss=%s" % (
        #     node_name, intf_name, intf_ip, destination, network, snapshot
        # ))
        status = self.register_snapshot(network, snapshot)
        snapshot_pattern = status["snapshot_pattern"]
        # Use orig snapshot to query intf_ip
        orig_snapshot = snapshot_pattern["orig_snapshot_name"] if snapshot_pattern is not None else snapshot
        intf_ip = self._get_interface_first_ip(network, orig_snapshot, node_name, intf_name)

        if self._is_disabled_intf(snapshot_pattern, node_name, intf_name):
            logger.info("traceroute: source %s[%s] is disabled in %s/%s" % (node_name, intf_name, network, snapshot))
            return {
                "network": network,
                "snapshot": snapshot,
                "result": [{"Flow": {}, "Traces": [{"disposition": "DISABLED", "hops": []}]}],
                "snapshot_pattern": snapshot_pattern,
            }

        self.bf.set_network(name=network)
        self.bf.set_snapshot(name=snapshot)
        frame = (
            self.bf.q.traceroute(
                startLocation=f"@enter({node_name}[{intf_name}])",
                headers=HeaderConstraints(dstIps=destination, srcIps=intf_ip),
            )
            .answer()
            .frame()
        )

        res = []
        for index, row in frame.iterrows():
            res.append(
                {
                    "Flow": self._rec_dict(row["Flow"]),
                    "Traces": self._rec_dict(row["Traces"]),
                }
            )

        return {"network": network, "snapshot": snapshot, "result": res, "snapshot_pattern": snapshot_pattern}
