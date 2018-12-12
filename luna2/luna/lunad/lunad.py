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
Boilerplate for lunad:app
"""
import pkgutil
import importlib
from flask import Flask
from lunad import extentions, lunad_blueprints

APP = Flask(__name__)

extentions.init_app(APP)

# TODO: Without ignoring type mypy will complain:
# 'Module has no attribute "__path__"'
# see https://github.com/python/mypy/issues/1422
for importer, modname, ispkg in pkgutil.iter_modules(
        lunad_blueprints.__path__):  # type: ignore

    if modname.endswith(APP.config['BLUEPRINT_SUFFIX']):
        fullmodname = "lunad.lunad_blueprints." + modname
        module = importlib.import_module(fullmodname, modname)
        APP.register_blueprint(
            getattr(module, modname[:-len(APP.config['BLUEPRINT_SUFFIX'])]),
            url_prefix=APP.config["APPLICATION_ROOT"]
        )
