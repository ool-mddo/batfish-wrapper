import json
import sys
from jinja2 import Environment, FileSystemLoader
from os import path

from .merge import get_diff, calc_reversed_diffs, get_node_and_template_name


def generate_config(original_asis, original_tobe):
    prod = []
    j2env = Environment(
        loader=FileSystemLoader(path.join(path.dirname(__file__), "templates")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    diff = get_diff(original_asis, original_tobe)
    rdiffs = calc_reversed_diffs(diff, original_asis)
    for rdiff in rdiffs:
        node_id, template_name = get_node_and_template_name(rdiff, original_asis)
        prod.append(
            {
                "node-id": node_id,
                "config": j2env.get_template(template_name).render(rdiff=rdiff),
            }
        )
    return prod
