import json
from uuid6 import uuid6
from datetime import datetime

from services.db import get_database

def lambda_handler(event, context):
    """
    Lógica para POST /templates:
    - Usa UUID v6 como _id
    - Usa global_key con prefijo + UUID
    - Toma created_by_user y updated_by_user desde sub (Cognito)
    - Toma id_client desde client_id (token)
    """
    try:
        db_name = event.get("db_name")
        if not db_name:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "No se recibió db_name en el evento"})
            }

        body = json.loads(event.get("body") or "{}")
        table_name = body.get("table_name")
        #valida si viene el table_name
        if not table_name and table_name!= "templates":
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Falta el campo 'table_name' en el cuerpo de la solicitud"})
            }
        
        db = get_database(db_name)
        collection = db[table_name]

        auth_result = event.get("auth_result", {})
        user_data = auth_result.get("user_data", {})

        created_by_user = user_data.get("sub") or "unknown"
        id_client = user_data.get("client_id") or "unknown"

        now_ts = int(datetime.now().timestamp())
        generated_id = str(uuid6())
        global_key_str = f"template_{generated_id}"
        
       

        new_item = {
            **body,
            "_id": generated_id,
            "id_client": id_client,           
            "_cls": "Template",
            "created_at": now_ts,
            "created_by": created_by_user,
            "updated_at": now_ts,
            "updated_by": created_by_user,
            "deleted": False,
            "status": True,
            "global_key": global_key_str
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
