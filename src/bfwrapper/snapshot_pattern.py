from __future__ import annotations
from typing import List, Union
from pybatfish.datamodel.primitives import Interface
from l1topology_edge import L1TopologyEdge, L1TopologyEdgeDict
from bf_wrapper_types import SnapshotPatternDict


class SnapshotPattern:
    def __init__(
        self,
        index: int,
        orig_snapshot_dir: str,
        orig_snapshot_name: str,
        source_snapshot_name: str,
        target_snapshot_name: str,
        lost_edges: List[Union[L1TopologyEdge, L1TopologyEdgeDict]],
        description: str,
    ) -> None:
        """Constructor
        Args:
            index (int): Index number of the snapshot pattern data
            orig_snapshot_dir (str): Directory path of origin (physical) snapshot
            orig_snapshot_name (str): name of origin (physical) snapshot
            source_snapshot_name (str): diff source snapshot name (physical(origin)/logical(draw-off))
            target_snapshot_name (str): fork target snapshot name (logical)
            lost_edges (List[L1TopologyEdge]): lost edges when fork snapshot
            description (str): Description of the (target) snapshot
        """
        self.index = index
        self.orig_snapshot_dir = orig_snapshot_dir
        self.orig_snapshot_name = orig_snapshot_name
        self.source_snapshot_name = source_snapshot_name
        self.target_snapshot_name = target_snapshot_name
        self.lost_edges = self._uniform_edges(lost_edges)
        self.description = description

    @staticmethod
    def _uniform_edges(edges: List[Union[L1TopologyEdge, L1TopologyEdgeDict]]) -> List[L1TopologyEdge]:
        """Edges dict to object
        Args:
            edges (List[Union[L1TopologyEdge, L1TopologyEdgeDict]]): Edges dict or object
        Returns:
            List[L1TopologyEdge]: Edges object
        """
        return [e if isinstance(e, L1TopologyEdge) else L1TopologyEdge(e) for e in edges]

    def to_dict(self) -> SnapshotPatternDict:
        """Convert to dict
        Returns:
            SnapshotPatternDict: Edges dict
        """
        return {
            "index": self.index,
            "orig_snapshot_dir": self.orig_snapshot_dir,
            "orig_snapshot_name": self.orig_snapshot_name,
            "source_snapshot_name": self.source_snapshot_name,
            "target_snapshot_name": self.target_snapshot_name,
            "lost_edges": [e.to_dict() for e in self.lost_edges],
            "description": self.description,
        }

    def deactivate_interfaces(self) -> List[Interface]:
        """Deactivate interfaces using snapshot pattern data
        Returns:
            List[Interface]: Interfaces to deactivate
        """
        interfaces = []
        for edge in self.lost_edges:
            interfaces.append(edge.node1.to_bf_interface())
            interfaces.append(edge.node2.to_bf_interface())
        return interfaces

    def owns_as_disabled_intf(self, node: str, intf: str) -> bool:
        """Test whether the interface is disabled or not in this snapshot
        Args:
            node: Node name
            intf: Interface name
        Returns:
            bool: True if specified node/intf is included in lost_edges of this snapshot-pattern
        """
        for lost_edge in self.lost_edges:
            if lost_edge.is_equal(node, intf):
                return True
        return False
