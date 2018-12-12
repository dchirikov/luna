# Written by Dmitry Chirikov <dmitry@chirikov.ru>
# Created in ClusterVision <infonl@clustervision.com>
#
# This file is part of Luna, cluster provisioning tool
# https://github.com/clustervision/luna
#
# This file is part of Luna.

# Luna is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Luna is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Luna.  If not, see <http://www.gnu.org/licenses/>.

"""
Multiple extensions for lunad
"""

from pathlib import Path
import logging
import os
import yaml
from yaml import YAMLError
from yaml.scanner import ScannerError
from flask_pymongo import PyMongo
from flask_json import FlaskJSON
from lunad.utils import JSONType, get_database_uri, LunadRuntimeError


LUNAD_CONFIG: JSONType = {}
MONGO = PyMongo()
JSON = FlaskJSON()

DEFAULT_LUNA_CONF = {
    "api_ver": "/api/v2",
    "store": {
        "path": str(Path.home())
    },
    "db": {
        "host": "localhost"
    },
}

DEFAULT_LUNA_CONF_FILE = '/etc/luna/lunad.conf'


def apply_defaults(
        conf: JSONType,
        defaults: JSONType = None,
        ) -> None:
    """
    Parse config and apply defaults
    if section or variable is undefined

    Modifies conf
    """
    if defaults is None:
        defaults = DEFAULT_LUNA_CONF
    for key, val in defaults.items():
        if isinstance(val, dict):
            apply_defaults(conf[key], val)
        else:
            if key not in conf:
                conf[key] = val


def get_config(app) -> JSONType:
    """
    Read config from ${LUNA_CONF} env variable
    or from DEFAULT_LUNA_CONF_FILE
    """
    conf_file = os.environ.get('LUNA_CONF') or DEFAULT_LUNA_CONF_FILE
    try:
        with open(conf_file) as fd_conf:
            try:
                yaml_config = yaml.load(fd_conf)
            except (ScannerError, YAMLError):
                msg = f"Error parsing {conf_file}"
                app.logger.error(msg)
                raise LunadRuntimeError(msg)
    except Exception as exc:  # pylint: disable=broad-except
        exception = str(exc)
        msg = f"Error while opening config file {conf_file}: {exception}"
        app.logger.error(msg)
        raise LunadRuntimeError(msg)
    return yaml_config


def configure_logger(app) -> None:
    """
    Allow lunad to use standard gunicorn logger
    """
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)


def init_app(app) -> None:
    """
    Configure app and add custom extentions:
    logging
    config
    mongo
    json
    """
    configure_logger(app)

    global LUNAD_CONFIG, MONGO  # pylint: disable=global-statement

    # read config file
    LUNAD_CONFIG = get_config(app)
    apply_defaults(LUNAD_CONFIG)

    # define boot and torrent dirs
    luna_path = LUNAD_CONFIG['store']['path']
    app.logger.info(f"Luna stores files in {luna_path}")

    boot_path = luna_path + '/boot'
    torrent_path = luna_path + '/torrents'

    # create boot and torrent dirs
    for path in [boot_path, torrent_path]:
        if not os.path.exists(path):
            os.makedirs(path)

    # auth token
    try:
        token = LUNAD_CONFIG['auth']['token']
    except KeyError:
        raise LunadRuntimeError("REST API token not found")

    app.config["MONGO_URI"] = get_database_uri(LUNAD_CONFIG)
    app.config['JSON_ADD_STATUS'] = False
    app.config["APPLICATION_ROOT"] = LUNAD_CONFIG['api_ver']
    app.config['BOOT_FILES_PATH'] = boot_path
    app.config['TORRENT_FILES_PATH'] = torrent_path
    app.config["AUTH_TOKEN"] = token
    app.config["BLUEPRINT_SUFFIX"] = "_blueprint"

    MONGO.init_app(app)
    JSON.init_app(app)
