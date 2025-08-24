import json
from uuid6 import uuid6
from datetime import datetime

from services.db import get_database
from middleware.auth_middleware import auth_middleware

@auth_middleware
def lambda_handler(event, context):
    try:
        auth_result = event.get("auth_result", {})
        user_data = auth_result.get("user_data", {})
        
        if not user_data.get("db_name"):
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "Unauthorized"})
            }

        db = get_database(user_data.get("db_name"))
        body = json.loads(event.get("body") or "{}")
        if not body or not isinstance(body, dict):
            return _response(400, {"error": "El body debe ser un JSON válido con campos a actualizar"})
        
        table_name = body.get("table_name")
        #valida si viene el table_name
        if not table_name:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Falta el campo 'table_name' en el cuerpo de la solicitud"})
            }
        collection = db[table_name]

        now_ts = int(datetime.now().timestamp())
        generated_id = str(uuid6())
        global_key_str = f"template_{generated_id}"

        #Eliminar el table_name del body
        body.pop("table_name", None)

        new_item = {
            **body,
            "_id": generated_id,
            "created_at": now_ts,
            "created_by": user_data.get("_id"),
            "updated_at": now_ts,
            "updated_by": user_data.get("_id"),
            "deleted": False,
            "status": True,
        }

        collection.insert_one(new_item)

        return {
            "statusCode": 201,
            "body": json.dumps({
                "message": f"Registro creado con ID {generated_id}",
                "item": new_item
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
