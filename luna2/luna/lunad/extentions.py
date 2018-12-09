from pathlib import Path
import logging
import os
import yaml
from flask_pymongo import PyMongo
from flask_json import FlaskJSON
from lunad.utils import get_database_uri


log = logging.getLogger("gunicorn.error")

lunad_config = {}
mongo = None
json = FlaskJSON()

default_conf = {
    "api_ver": "/api/v2",
    "store": {
        "path": str(Path.home())
    },
    "db": {
        "host": "localhost"
    },
}

DEFAULT_LUNA_CONF = '/etc/luna/lunad.conf'


def apply_defaults(conf, defaults=default_conf):
    for k, v in defaults.items():
        if isinstance(v, dict):
            apply_defaults(conf[k], v)
        else:
            if k not in conf:
                conf[k] = v


def get_config(app=None):
    if app is None:
        log = logging.getLogger()
    else:
        log = app.logger
    conf_file = os.environ.get('LUNA_CONF') or DEFAULT_LUNA_CONF
    try:
        with open(conf_file) as f:
            try:
                yaml_config = yaml.load(f)
            except (yaml.scanner.ScannerError, yaml.YAMLError):
                log.error(f"Error parsing {conf_file}")
                return None
    except Exception as e:
        log.error(f"Error while opening config file {conf_file}: {e}")
        return None
    return yaml_config


def init_app(app):
    global lunad_config, mongo
    lunad_config = get_config(app)
    apply_defaults(lunad_config)
    app.config["MONGO_URI"] = get_database_uri(lunad_config)
    mongo = PyMongo(app)
    app.config['JSON_ADD_STATUS'] = False
    json.init_app(app)
