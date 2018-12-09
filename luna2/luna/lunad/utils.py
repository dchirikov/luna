from flask import current_app as app
from flask import request
from functools import wraps
from urllib.parse import quote_plus


class LunadRuntimeError(Exception):
    pass


def get_database_uri(lunad_conf):
    if 'db' not in lunad_conf:
        return {'host': "localhost"}

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
