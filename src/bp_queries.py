import os
import shutil
from flask import Blueprint, request, jsonify, Response
from app_common import QUERIES_DIR, bfqt

bp_queries = Blueprint("queries", __name__, url_prefix="/queries")


@bp_queries.route("/<network>", methods=["DELETE"])
def delete_queries(network: str) -> Response:
    """Delete all query results
    Args:
        network (str): Network name
    """
    try:
        shutil.rmtree(os.path.join(QUERIES_DIR, network))
    except FileNotFoundError:
        pass  # silent remove
    return jsonify({})


@bp_queries.route("/<network>", methods=["POST"])
def post_queries_for_all_snapshots(network: str) -> Response:
    """Post query request for all snapshots
    Args:
        network (str): Network name
    Returns:
        Response: List[WholeQuerySummaryDict]
    Note:
        POST parameter:
        * query (str): Optional: target query (limit a query)
    """
    req = request.json
    query = req["query"] if "query" in req else None
    resp = bfqt.exec_queries_for_all_snapshots(network, query)
    return jsonify(resp)


@bp_queries.route("/<network>/<snapshot>", methods=["POST"])
def post_queries(network: str, snapshot: str) -> Response:
    """Post query request for a snapshot
    Args:
        network (str): Network name
        snapshot (str): Snapshot name
    Returns:
        Response: List[WholeQuerySummaryDict]
    Note:
        POST parameter:
        * query (str): Optional: target query (limit a query)
    """
    req = request.json
    query = req["query"] if "query" in req else None
    resp = bfqt.exec_queries(network, snapshot, query)
    return jsonify(resp)
