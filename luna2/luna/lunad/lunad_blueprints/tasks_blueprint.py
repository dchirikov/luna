"""
Flask blueprint for /tasks entrypoint
"""
from typing import Dict, List
from flask import Blueprint, request
from bson.objectid import ObjectId
from flask_json import json_response, as_json
from lunad.utils import auth_required
from lunad.extentions import MONGO

SUFFIX = '_blueprint'
ROUTE_NAME = __name__.split('.')[-1]
if ROUTE_NAME.endswith(SUFFIX):
    ROUTE_NAME = ROUTE_NAME[:-len(SUFFIX)]

globals()[ROUTE_NAME] = Blueprint(name=ROUTE_NAME, import_name=ROUTE_NAME)

BLUEPRINT = globals()[ROUTE_NAME]


# curl -i -X POST -H "Authorization: Token  ${TOKEN}" \
#       --data '{"aaa": 111, "bbb": 222}' \
#       http://localhost:6000/api/v2/tests
@BLUEPRINT.route(f"/{ROUTE_NAME}", methods=['POST'])
@auth_required
@as_json
def create_item() -> Dict[str, str]:
    """
    Create task, Return id of the task
    """
    data = request.get_json(force=True)
    oid = MONGO.db.tests.insert_one(data).inserted_id
    return {"id": str(oid)}


# curl -i -X GET -H "Authorization: Token ${TOKEN}" \
#       http://localhost:6000/api/v2/tests
@BLUEPRINT.route(f"/{ROUTE_NAME}", methods=['GET'])
@auth_required
@as_json
def list_items() -> List[Dict[str, str]]:
    """
    Return list of the tasks
    """
    docs = MONGO.db.tests.find()
    data = []
    for doc in docs:
        data.append({"id": str(doc["_id"])})
    return data


# curl -i -X GET -H "Authorization: Token ${TOKEN}" \
#       http://localhost:6000/api/v2/tests/5c0da09dac4f4e0421a24a98
@BLUEPRINT.route(f"/{ROUTE_NAME}/<_id>")
@auth_required
@as_json
def get_item_info(_id) -> Dict[str, str]:
    """
    Return info about task
    """
    try:
        data = MONGO.db.tests.find_one_or_404({"_id": ObjectId(_id)})
    except RuntimeError as exc:
        return json_response(status_=400, error=str(exc))

    data["id"] = str(data.pop("_id"))
    return data
