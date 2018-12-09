from flask import Blueprint, request
from flask import current_app as app
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
import os
from lunad.extentions import mongo
from lunad.utils import auth_required
from flask_json import json_response, as_json

suffix = '_blueprint'
ROUTE_NAME = __name__.split('.')[-1]
if ROUTE_NAME.endswith(suffix):
    ROUTE_NAME = ROUTE_NAME[:-len(suffix)]

globals()[ROUTE_NAME] = Blueprint(name=ROUTE_NAME, import_name=ROUTE_NAME)

BLUEPRINT = globals()[ROUTE_NAME]


# curl -i -X POST -H "Authorization: Token  ${TOKEN}" \
#       --data '{"aaa": 111, "bbb": 222}' \
#       http://localhost:6000/api/v2/tests
@BLUEPRINT.route(f"/{ROUTE_NAME}", methods=['POST'])
@auth_required
@as_json
def create_item():
    data = request.get_json(force=True)
    oid = mongo.db.tests.insert_one(data).inserted_id
    return {"id": str(oid)}


# curl -i -X GET -H "Authorization: Token ${TOKEN}" \
#       http://localhost:6000/api/v2/tests
@BLUEPRINT.route(f"/{ROUTE_NAME}", methods=['GET'])
@auth_required
@as_json
def list_items():
    docs = mongo.db.tests.find()
    data = []
    for d in docs:
        data.append({"id": str(d["_id"])})
    return data


# curl -i -X GET -H "Authorization: Token ${TOKEN}" \
#       http://localhost:6000/api/v2/tests/5c0da09dac4f4e0421a24a98
@BLUEPRINT.route(f"/{ROUTE_NAME}/<id>")
@auth_required
@as_json
def get_item_info(id):
    try:
        data = mongo.db.tests.find_one_or_404({"_id": ObjectId(id)})
    except Exception as e:
        return json_response(status_=400, error=str(e))

    data["id"] = str(data.pop("_id"))
    return data
