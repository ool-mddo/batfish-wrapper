import app_common as ac
from bp_batfish import bp_batfish
from bp_configs import bp_configs
from bp_queries import bp_queries
from bp_tools import bp_tools

ac.app.register_blueprint(bp_batfish)
ac.app.register_blueprint(bp_configs)
ac.app.register_blueprint(bp_queries)
ac.app.register_blueprint(bp_tools)


if __name__ == "__main__":
    ac.app.run(debug=True, host="0.0.0.0", port=5000)
