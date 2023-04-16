import os
import logging
from flask import Flask
from flask.logging import create_logger
from bfwrapper.loglevel import set_loglevel
from bfwrapper.bf_query_thrower import BatfishQueryThrower

app = Flask(__name__)
app_logger = create_logger(app)
logging.basicConfig(level=logging.WARNING)

set_loglevel("pybatfish", os.environ.get("BATFISH_WRAPPER_PYBATFISH_LOG_LEVEL", "warning"))
set_loglevel("bfwrapper", os.environ.get("BATFISH_WRAPPER_LOG_LEVEL", "info"))

BATFISH_HOST = os.environ.get("BATFISH_HOST", "localhost")
CONFIGS_DIR = os.environ.get("MDDO_CONFIGS_DIR", "./configs")
QUERIES_DIR = os.environ.get("MDDO_QUERIES_DIR", "./queries")

# pylint: disable=too-many-function-args
bfqt = BatfishQueryThrower(BATFISH_HOST, CONFIGS_DIR, QUERIES_DIR)
