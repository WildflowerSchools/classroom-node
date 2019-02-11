import json

from flask import Flask, make_response

from camnode.honeycombproxy.v1.views import v1

app = Flask(__name__)


@app.route("/", methods=['GET'])
def root_handler():
    return make_response(json.dumps({"status": "ok"}), 200)



app.register_blueprint(v1, url_prefix="/v1")
