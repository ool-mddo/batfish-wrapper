"""
Definition of SimulationPatternGenerator class
"""
import json
import re
from os import path
from typing import List, Optional, TypedDict
from l1topology_edge import L1TopologyEdge
from l1topology_operator import L1TopologyOperator
from snapshot_pattern import SnapshotPattern
from bf_wrapper_types import SnapshotPatternDict


class LabeledEdgesDict(TypedDict):
    lost_edges: List[L1TopologyEdge]
    found_edges: List[L1TopologyEdge]


class SimulationPatternGenerator(L1TopologyOperator):
    """Simulation pattern generator"""

    def __init__(self, network: str, snapshot: str, configs_dir: str) -> None:
        """Constructor
        Args:
            network (str): Network name
            snapshot (str): Snapshot name
            configs_dir (str): Path of 'configs' directory (contains batfish network/snapshot directories)
        """
        super().__init__(network, snapshot, configs_dir)
        self.drawoff_node = ""
        self.drawoff_intf_re = re.compile(r".*")  # default: match all interfaces of target node

    def _label_edges(self, edges: List[L1TopologyEdge]) -> LabeledEdgesDict:
        """Label edges list to lost/found edges
        Args:
            edges (List[L1TopologyEdge]): whole edges
        Returns:
            LabeledEdgesDict: 'lost_edges' and 'found_edges'
        """
        return {
            "lost_edges": [e for e in edges if e.is_match(self.drawoff_node, self.drawoff_intf_re)],
            "found_edges": [e for e in edges if not e.is_match(self.drawoff_node, self.drawoff_intf_re)],
        }

    def _make_drawoff_snapshot_pattern(self, edges: List[L1TopologyEdge]) -> SnapshotPattern:
        """Make draw-off snapshot pattern data
        Args:
            edges (List[L1TopologyEdge]): whole edges
        Returns:
            SnapshotPattern: Snapshot pattern (draw-off snapshot)
        """
        labeled_edges = self._label_edges(edges)
        return SnapshotPattern(
            0,
            self.snapshot_dir_path,
            self.snapshot,
            self.snapshot,
            f"{self.snapshot}_drawoff",
            labeled_edges["lost_edges"],
            f"Draw-off node: {self.drawoff_node}, link_pattern: {self.drawoff_intf_re.pattern}",
        )

    def _make_linkdown_snapshot_patterns(
        self, edges: List[L1TopologyEdge], drawoff_snapshot_pattern: Optional[SnapshotPattern] = None
    ) -> List[SnapshotPattern]:
        """Make link-down snapshot pattern data
        Args:
            edges (List[L1TopologyEdge]): whole edges
            drawoff_snapshot_pattern (Optional[SnapshotPattern]): draw-off snapshot pattern
        Returns:
            List[SnapshotPattern]: Snapshot pattern (link-down snapshots)
        """
        drawoff_edges: List[L1TopologyEdge] = []
        drawoff_snapshot_name = self.snapshot
        if drawoff_snapshot_pattern is not None:
            drawoff_edges = drawoff_snapshot_pattern.lost_edges
            drawoff_snapshot_name = drawoff_snapshot_pattern.target_snapshot_name
            self.logger.info("drawoff_snapshot name : %s", drawoff_snapshot_name)
            self.logger.info("drawoff_snapshot edges: %s", [str(e) for e in drawoff_edges])

        snapshot_patterns = []
        for i, edge in enumerate(self.filter_edges(edges, drawoff_edges)):
            index = i + 1  # index number start 1
            snapshot_pattern = SnapshotPattern(
                index,
                self.snapshot_dir_path,
                self.snapshot,
                drawoff_snapshot_name,
                f"{self.snapshot}_linkdown_{index:02}",
                drawoff_edges + [edge],
                f"Link-down No.{index:02}: {edge} (L1)",
            )
            self.logger.info("linkdown %02d: %s", index, snapshot_pattern.description)
            snapshot_patterns.append(snapshot_pattern)

        return snapshot_patterns

    def _make_snapshot_patterns(self) -> List[SnapshotPattern]:
        """Make draw-off/link-down snapshot pattern data
        Returns:
            List[SnapshotPattern]: all snapshot patterns
        """
        # deduplicate edges (layer1_topology link definition is bidirectional)
        uniq_edges = self._deduplicate_edges(self.edges)

        # make draw-off snapshot info at first
        drawoff_snapshot_pattern = None
        if self.drawoff_node is not None:
            drawoff_snapshot_pattern = self._make_drawoff_snapshot_pattern(uniq_edges)

        # make link-down snapshot info
        linkdown_snapshot_patterns = self._make_linkdown_snapshot_patterns(uniq_edges, drawoff_snapshot_pattern)

        if drawoff_snapshot_pattern is None:
            return linkdown_snapshot_patterns
        return [drawoff_snapshot_pattern] + linkdown_snapshot_patterns

    def _write_snapshot_patterns(self, pattern_data: List[SnapshotPatternDict]) -> None:
        """Save snapshot pattern data to file
        Args:
            pattern_data (List[SnapshotPatternDict]): snapshot pattern data to save
        Returns:
            None
        """
        with open(path.join(self.snapshot_dir_path, "snapshot_patterns.json"), "w", encoding="utf-8") as file:
            json.dump(pattern_data, file, indent=2)

    def make_snapshot_patterns(
        self, node: Optional[str] = None, intf_re: Optional[str] = None
    ) -> List[SnapshotPatternDict]:
        """Make and save all snapshot patterns
        Args:
            node (Optional[str]): Node name to draw-off
            intf_re (Optional[str]): Interface name regexp to detect draw-off link of the node
        Returns:
              List[SnapshotPatternDict]: Snapshot pattern data
        """
        self.drawoff_node = node
        if self.drawoff_node is not None and intf_re is not None:
            self.drawoff_intf_re = re.compile(intf_re, flags=re.IGNORECASE)
        snapshot_patterns = self._make_snapshot_patterns()
        snapshot_pattern_dicts = [ptn.to_dict() for ptn in snapshot_patterns]
        self._write_snapshot_patterns(snapshot_pattern_dicts)
        return snapshot_pattern_dicts
