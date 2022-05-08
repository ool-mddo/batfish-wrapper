"""
Definition of BatfishRegistrant class
"""
from typing import List, Dict, Optional, Any
import pandas as pd
from pybatfish.datamodel.flow import HeaderConstraints
from bf_registrant_base import BatfishRegistrantBase
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
        Note:
            Cannot respond for server (hosts defined node)
        """
        self.bf_session.set_network(network)
        self.bf_session.set_snapshot(snapshot)
        # pylint: disable=no-member
        return self.bf_session.q.interfaceProperties(nodes=node).answer().frame()

    def _get_interface_first_ip(self, network: str, snapshot: str, node: str, interface: str) -> str:
        """Get ip address (without CIDR) of node and interface
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
            node (str): Node name
            interface (str): Interface name
        Returns:
            str: IP address (without netmask "/x")
        """
        self.bf_session.set_network(name=network)
        self.bf_session.set_snapshot(name=snapshot)
        intf_ip_prefix = (
            # pylint: disable=no-member
            self.bf_session.q.interfaceProperties(nodes=node, interfaces=interface)
            .answer()
            .frame()
            .to_dict()["All_Prefixes"][0][0]
        )
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

    def get_snapshot_patterns(self, network: str, snapshot: str) -> List[SnapshotPatternDict]:
        """Get snapshot patterns
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
        Returns:
            List[SnapshotPatternDict]:
        """
        if self._is_physical_snapshot(network, snapshot):
            return [e.to_dict() for e in self._read_snapshot_patterns(network, snapshot)]

        # for logical snapshot
        pattern = self._find_snapshot_pattern(network, snapshot)
        return [pattern.to_dict()] if pattern is not None else []

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

    def exec_traceroute_query(
        self, network: str, snapshot: str, node: str, intf: str, destination: str, logger
    ) -> TracerouteQueryStatus:
        """Query traceroute
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
            node (str): Node name (source)
            intf (str): Interface name (source)
            destination (str): Traceroute destination
            logger: Logger
        Returns:
            TracerouteQueryStatus: Query answer
        """
        # app.logger.debug("_traceroute: node=%s intf=%s intf_ip=%s dst=%s nw=%s ss=%s" % (
        #     node_name, intf_name, intf_ip, destination, network, snapshot
        # ))

        # prepare snapshot
        status = self.register_snapshot(network, snapshot)
        snapshot_pattern = status.snapshot_pattern
        # Use orig snapshot to query intf_ip
        orig_snapshot = snapshot_pattern.orig_snapshot_name if snapshot_pattern is not None else snapshot
        intf_ip = self._get_interface_first_ip(network, orig_snapshot, node, intf)

        # source node/interface is disabled?
        if snapshot_pattern is not None and snapshot_pattern.owns_as_disabled_intf(node, intf):
            logger.info(f"traceroute: source {node}[{intf}] is disabled in {network}/{snapshot}")
            return {
                "network": network,
                "snapshot": snapshot,
                "result": [{"Flow": {}, "Traces": [{"disposition": "DISABLED", "hops": []}]}],
                "snapshot_pattern": snapshot_pattern.to_dict(),
            }

        # query traceroute
        answer = self._query_traceroute(network, snapshot, node, intf, intf_ip, destination)
        return {
            "network": network,
            "snapshot": snapshot,
            "result": answer,
            "snapshot_pattern": snapshot_pattern.to_dict() if snapshot_pattern is not None else None,
        }
