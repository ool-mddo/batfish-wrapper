from flask import Blueprint, request, jsonify, Response
from model_merge.config import generate_config

bp_tools = Blueprint("tools", __name__, url_prefix="/tools")


@bp_tools.route("/model-merge", methods=["POST"])
def get_diff_config() -> Response:
    """Calc diff and generate config
    Data:
        {"asis": ..., "tobe": ...}
    Returns:
        Response: {device name and config}
    """
    req = request.json
    res = generate_config(req["asis"], req["tobe"])
    return jsonify(res)
