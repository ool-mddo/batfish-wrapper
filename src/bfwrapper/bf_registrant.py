"""
Definition of BatfishRegistrant class
"""
from typing import List, Dict, Optional, Any
import pandas as pd
from pybatfish.datamodel.flow import HeaderConstraints
from bf_registrant_base import BatfishRegistrantBase, SnapshotPattern
from bf_wrapper_types import SnapshotPatternDict, TracerouteQueryStatus


class BatfishRegistrant(BatfishRegistrantBase):
    """Batfish registrant"""

    def bf_node_list(self, network: str, snapshot: str) -> pd.DataFrame:
        """Query node properties table to batfish
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
        Returns:
            pd.DataFrame: Query answer
        """
        self.bf_session.set_network(network)
        self.bf_session.set_snapshot(snapshot)
        # pylint: disable=no-member
        return self.bf_session.q.nodeProperties().answer().frame()

    def bf_interface_list(self, network: str, snapshot: str) -> pd.DataFrame:
        """Query interface properties to batfish
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
        Returns:
            pd.DataFrame: Query answer
        """
        self.bf_session.set_network(network)
        self.bf_session.set_snapshot(snapshot)
        # pylint: disable=no-member
        return self.bf_session.q.interfaceProperties().answer().frame()

    def bf_node_interface_list(self, network: str, snapshot: str, node: str) -> pd.DataFrame:
        """Query interface properties with node
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
            node (str): Node name
        Returns:
            pd.DataFrame: Query answer
        """
        self.bf_session.set_network(network)
        self.bf_session.set_snapshot(snapshot)
        # pylint: disable=no-member
        return self.bf_session.q.interfaceProperties(nodes=node).answer().frame()

    def _get_interface_first_ip(self, network: str, snapshot: str, node: str, interface: str) -> [str, None]:
        """Get ip address (without CIDR) of node and interface
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
            node (str): Node name
            interface (str): Interface name
        Returns:
            [str, None]: IP address (without netmask "/x") or None if the interface doesn't have IP address
        """
        self.bf_session.set_network(name=network)
        self.bf_session.set_snapshot(name=snapshot)
        intf_ip_prefix_list = (
            # pylint: disable=no-member
            # NOTE: normalize node name
            self.bf_session.q.interfaceProperties(nodes=node.lower(), interfaces=interface)
            .answer()
            .frame()
            .to_dict()["All_Prefixes"][0]
        )
        if len(intf_ip_prefix_list) < 1:
            # e.g. for layer2 interface, it does not have ip address
            return None

        intf_ip_prefix = intf_ip_prefix_list[0]
        return intf_ip_prefix[: intf_ip_prefix.find("/")]

    def get_batfish_snapshots(self, network: Optional[str] = None) -> Dict[str, List[str]]:
        """Get snapshots from batfish
        Args:
            network (str): Network name
        Returns:
            Dict[str, List[str]]]: Dict of key: network name (str) and value: a list of snapshot names (str)
        """
        bf_networks = [network] if network else self.bf_networks()
        ret = {}
        for bf_network in bf_networks:
            ret[bf_network] = self.bf_snapshots(bf_network)
        return ret

    def get_snapshot_patterns(self, network: str, snapshot: str) -> [List[SnapshotPatternDict], SnapshotPatternDict]:
        """Get snapshot patterns
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
        Returns:
            [List[SnapshotPatternDict], SnapshotPatternDict]: List for physical snapshot or Dict for logical snapshot
        """
        if self._is_physical_snapshot(network, snapshot):
            return [e.to_dict() for e in self._read_snapshot_patterns(network, snapshot)]

        # for logical snapshot
        pattern = self._find_snapshot_pattern(network, snapshot)
        return pattern.to_dict() if pattern is not None else []

    # traceroute-query related functions

    def _obj_to_dict(self, obj: Any) -> [List, Dict]:
        """Translate obj into dict structure recursively
        Args:
            obj (List, Dict): Object
        Returns:
            [List, Dict]: Translated object
        """
        if isinstance(obj, dict):
            return {key: self._obj_to_dict(value) for key, value in obj.items()}

        if hasattr(obj, "__iter__") and not isinstance(obj, str):
            return [self._obj_to_dict(value) for value in obj]

        if hasattr(obj, "__dict__"):
            return {
                key: self._obj_to_dict(value)
                for key, value in obj.__dict__.items()
                if not callable(value) and not key.startswith("_")
            }

        return obj

    def _query_traceroute(
        self, network: str, snapshot: str, node: str, intf: str, intf_ip: str, destination: str
    ) -> List[Dict]:
        """Query traceroute to batfish
            network (str): Network name
            snapshot (str): Snapshot name
            node (str): Node name (source)
            intf (str): Interface name (source)
            intf_ip (str): IP address of interface (source)
            destination (str): Traceroute destination (destination ip address)
        Returns:
            List[Dict]: Query answer
        """
        self.bf_session.set_network(name=network)
        self.bf_session.set_snapshot(name=snapshot)
        frame = (
            # pylint: disable=no-member
            self.bf_session.q.traceroute(
                startLocation=f"@enter({node}[{intf}])",
                headers=HeaderConstraints(srcIps=intf_ip, dstIps=destination),
            )
            .answer()
            .frame()
        )
        # convert data
        return [
            {"Flow": self._obj_to_dict(row["Flow"]), "Traces": self._obj_to_dict(row["Traces"])}
            for _index, row in frame.iterrows()
        ]

    def _find_ip_addr_from_lost_edges(
        self,
        network: str,
        snapshot: str,
        snapshot_pattern: SnapshotPattern,
        target_ip: str,
    ) -> [str, None]:
        """IP address list of lost_edge of the snapshot
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
            snapshot_pattern (SnapshotPattern): Snapshot pattern
            target_ip (str): IP address to find
        Returns:
            [str, None]: Found ip address or None if not found
        """
        ip_addrs = []
        for edge in snapshot_pattern.lost_edges:
            ip_addrs.append(self._get_interface_first_ip(network, snapshot, edge.node1.host, edge.node1.intf))
            ip_addrs.append(self._get_interface_first_ip(network, snapshot, edge.node2.host, edge.node2.intf))
        return next((ip for ip in ip_addrs if ip == target_ip), None)

    @staticmethod
    def _traceroute_result(
        network: str, snapshot: str, traceroute_answer: List[Dict], snapshot_pattern: Optional[SnapshotPattern] = None
    ) -> TracerouteQueryStatus:
        """Traceroute result
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
            traceroute_answer (List[Dict]): An answer of traceroute query
            snapshot_pattern (SnapshotPattern): Snapshot pattern
        Returns:
            TracerouteQueryStatus: Query answer
        """
        return {
            "network": network,
            "snapshot": snapshot,
            "result": traceroute_answer,
            "snapshot_pattern": snapshot_pattern.to_dict() if snapshot_pattern is not None else None,
        }

    @staticmethod
    def _disabled_traceroute_answer():
        return [{"Flow": {}, "Traces": [{"disposition": "DISABLED", "hops": []}]}]

    def exec_traceroute_query(
        self, network: str, snapshot: str, node: str, intf: str, destination: str
    ) -> TracerouteQueryStatus:
        """Query traceroute
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
            node (str): Node name (source)
            intf (str): Interface name (source)
            destination (str): Traceroute destination
        Returns:
            TracerouteQueryStatus: Query answer
        """
        # prepare snapshot
        status = self.register_snapshot(network, snapshot)
        snapshot_pattern = status.snapshot_pattern
        # Use orig snapshot to query intf_ip
        orig_snapshot = snapshot_pattern.orig_snapshot_name if snapshot_pattern is not None else snapshot
        intf_ip = self._get_interface_first_ip(network, orig_snapshot, node, intf)

        # for logical snapshot
        if snapshot_pattern is not None:
            # source node/interface is disabled?
            if snapshot_pattern.owns_as_disabled_intf(node, intf):
                print(f"# traceroute: source {node}[{intf}] is disabled in {network}/{snapshot}")
                return self._traceroute_result(network, snapshot, self._disabled_traceroute_answer(), snapshot_pattern)
            # destination ip is disabled?
            # NOTICE: if the network/snapshot has duplicated ip address, it cannot work fine, probably.
            if self._find_ip_addr_from_lost_edges(network, snapshot, snapshot_pattern, destination):
                print(f"# traceroute: destination {destination} is disabled in {network}/{snapshot}")
                return self._traceroute_result(network, snapshot, self._disabled_traceroute_answer(), snapshot_pattern)

        # query traceroute
        answer = self._query_traceroute(network, snapshot, node, intf, intf_ip, destination)
        return self._traceroute_result(network, snapshot, answer, snapshot_pattern)
