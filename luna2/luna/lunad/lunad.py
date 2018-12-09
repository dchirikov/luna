#!/env/bin/python
import pkgutil
import importlib
from flask import Flask, g
from lunad.utils import LunadRuntimeError, get_database_uri
import logging
import os
from pathlib import Path
from lunad import extentions, lunad_blueprints

app = Flask(__name__)

# use gunicorn logger
gunicorn_logger = logging.getLogger("gunicorn.error")
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)

extentions.init_app(app)

# app config
app.config["APPLICATION_ROOT"] = extentions.lunad_config['api_ver']

# define boot and torrent dirs
luna_path = extentions.lunad_config['store']['path']

app.logger.info(f"Luna stores files in {luna_path}")

boot_path = luna_path + '/boot'
torrent_path = luna_path + '/torrents'

app.config['BOOT_FILES_PATH'] = boot_path
app.config['TORRENT_FILES_PATH'] = torrent_path

# create boot and torrent dirs
for path in [boot_path, torrent_path]:
    if not os.path.exists(path):
        os.makedirs(path)

# auth token
try:
    token = extentions.lunad_config['auth']['token']
except KeyError:
    raise LunadRuntimeError("REST API token not found")

app.config['AUTH_TOKEN'] = token

# db connection settings
#app.config["MONGO_URI"] = get_database_uri(extentions.lunad_config)

blueprints_suffix = "_blueprint"

for importer, modname, ispkg in pkgutil.iter_modules(
        lunad_blueprints.__path__):

    if modname.endswith(blueprints_suffix):
        fullmodname = "lunad.lunad_blueprints." + modname
        module = importlib.import_module(fullmodname, modname)
        app.register_blueprint(
            getattr(module, modname[:-len(blueprints_suffix)]),
            url_prefix=app.config["APPLICATION_ROOT"]
        )
