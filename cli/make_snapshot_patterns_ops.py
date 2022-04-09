import json
import re
from os import path
import sys

sys.path.append(path.dirname(__file__))  # TODO: PYTHONPATH configuration
from l1_topology_operator import L1TopologyOperator


class SimulationPatternGenerator(L1TopologyOperator):
    def __init__(self, configs_dir, network, snapshot):
        super().__init__(configs_dir, network, snapshot)
        self.drawoff_node = ""
        self.drawoff_link_re = r".*"  # default: match all interfaces of target node

    @staticmethod
    def _make_snapshot_pattern(
        index,
        orig_snapshot_dir,
        orig_snapshot_name,
        source_snapshot_name,
        target_snapshot_name,
        edges,
        description,
    ):
        return {
            "index": index,
            "lost_edges": edges,
            "orig_snapshot_dir": orig_snapshot_dir,
            "orig_snapshot_name": orig_snapshot_name,
            "source_snapshot_name": source_snapshot_name,
            "target_snapshot_name": target_snapshot_name,
            "description": description,
        }

    def _match_lost_edge(self, edge, key):
        return edge[key]["hostname"].lower() == self.drawoff_node.lower() and re.fullmatch(
            self.drawoff_link_re, edge[key]["interfaceName"]
        )

    def _draw_off(self, edges):
        l1topo_lost = []
        l1topo_found = []

        for edge in edges:
            if self._match_lost_edge(edge, "node1") or self._match_lost_edge(edge, "node2"):
                l1topo_lost.append(edge)
            else:
                l1topo_found.append(edge)

        return {"lost_edges": l1topo_lost, "found_edges": l1topo_found}

    def _make_drawoff_snapshot_pattern(self, edges):
        drawoff_edges = self._draw_off(edges)
        return self._make_snapshot_pattern(
            0,
            self.snapshot_dir_path,
            self.snapshot,
            self.snapshot,
            "%s_drawoff" % self.snapshot,
            drawoff_edges["lost_edges"],
            "Draw-off node: %s, link_pattern: %s" % (self.drawoff_node, self.drawoff_link_re),
        )

    def _make_linkdown_snapshot_patterns(self, edges, drawoff_snapshot_pattern):
        drawoff_edges = []
        drawoff_snapshot_name = self.snapshot
        if drawoff_snapshot_pattern is not None:
            drawoff_edges = drawoff_snapshot_pattern["lost_edges"]
            drawoff_snapshot_name = drawoff_snapshot_pattern["target_snapshot_name"]
            print("# drawoff_snapshot_pattern")
            print("# - drawoff_edges: %s" % drawoff_edges)
            print("# - drawoff_snapshot_name: %s" % drawoff_snapshot_name)

        snapshot_patterns = []
        for i, edge in enumerate(self.filter_edges(edges, drawoff_edges)):
            index = i + 1  # index number start 1
            snapshot_pattern = self._make_snapshot_pattern(
                index,
                self.snapshot_dir_path,
                self.snapshot,
                drawoff_snapshot_name,
                "%s_linkdown_%02d" % (self.snapshot, index),
                drawoff_edges + [edge],
                "Link-down No.%02d: " % index + "%s[%s] <=> %s[%s] (L1)" % self._edge2tuple(edge),
            )
            print("# linkdown %02d: %s" % (index, snapshot_pattern["description"]))
            snapshot_patterns.append(snapshot_pattern)

        return snapshot_patterns

    def _make_snapshot_patterns(self):
        # deduplicate edges (layer1_topology link definition is bidirectional)
        uniq_edges = self._deduplicate_edges(self.l1_topology_data["edges"])

        # make draw-off snapshot info at first
        drawoff_snapshot_pattern = None
        if self.drawoff_node is not None:
            drawoff_snapshot_pattern = self._make_drawoff_snapshot_pattern(uniq_edges)

        # make link-down snapshot info
        linkdown_snapshot_patterns = self._make_linkdown_snapshot_patterns(uniq_edges, drawoff_snapshot_pattern)

        if drawoff_snapshot_pattern is None:
            return linkdown_snapshot_patterns
        return [drawoff_snapshot_pattern] + linkdown_snapshot_patterns

    def _write_snapshot_patterns(self, pattern_data):
        with open(path.join(self.snapshot_dir_path, "snapshot_patterns.json"), "w") as file:
            json.dump(pattern_data, file, indent=2)

    def make_snapshot_patterns(self, node, link_regexp):
        self.drawoff_node = node
        self.drawoff_link_re = re.compile(link_regexp, flags=re.IGNORECASE) if link_regexp else r".*"
        snapshot_patterns = self._make_snapshot_patterns()
        self._write_snapshot_patterns(snapshot_patterns)
        return snapshot_patterns
