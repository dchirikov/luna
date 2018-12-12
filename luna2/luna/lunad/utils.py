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
Shared helpers for lunad
"""
from urllib.parse import quote_plus
from typing import Any
from functools import wraps
from flask import current_app as app
from flask import request

# TODO: It is hard to define JSON properly, so will use this stub
# see https://github.com/python/typing/issues/182
JSONType = Any  # pylint: disable=invalid-name


class LunadRuntimeError(Exception):
    """
    General lunad exception
    """


def get_database_uri(lunad_conf: JSONType) -> str:
    """
    Parse config and return MongoDB
    """
    if 'db' not in lunad_conf:
        return "mongodb://localhost"

    con_options = lunad_conf["db"]
    con_options["host"] = "mongodb://"

    if "password" in con_options:
        con_options["password"] = quote_plus(con_options["password"])

    if "user" in con_options and "password" in con_options:
        con_options["host"] += con_options["user"]
        con_options["host"] += ":"
        con_options["host"] += con_options["password"]
        con_options["host"] += "@"

    if "server" in con_options:
        con_options["host"] += con_options["server"]
    else:
        con_options["host"] += "localhost"

    if "authdb" in con_options:
        con_options["host"] += "/" + con_options["authdb"]

    return con_options["host"]


def auth_required(func):
    """
    Decorator to check if request is authenticated
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        error = '{"Error": "No auth"}', 403
        if 'Authorization' not in request.headers:
            return error
        try:
            method, token = request.headers['Authorization'].split()
        except ValueError:
            return error
        if method != 'Token':
            return error
        if token == app.config['AUTH_TOKEN']:
            return func(*args, **kwargs)
        return error

    return decorated_function
