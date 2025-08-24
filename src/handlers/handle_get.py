# handlers/handle_get.py
import os
import json
from services.db import get_database
from pymongo.errors import ServerSelectionTimeoutError
from middleware.auth_middleware import auth_middleware

@auth_middleware
def lambda_handler(event, context):
    # permission_middleware = permission_middleware(event, context)

    # if permission_middleware is not True:
    #     return permission_middleware
    
    auth_result = event.get("auth_result", {})
    user_data = auth_result.get("user_data", {})
    
    if not user_data.get("db_name"):
        return {
            "statusCode": 403,
            "body": json.dumps({"error": "Unauthorized"})
        }
    
    table_name = event.get("queryStringParameters", {}).get("table_name")

    #valida si viene el table_name
    if not table_name:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Falta el campo 'table_name' en el cuerpo de la solicitud"})
        }
    try:
        db = get_database(user_data.get("db_name"))
        collection = db[table_name]
        module_id = event.get("pathParameters", {}).get("id")
        if module_id:
            try:
                doc = collection.find_one({"_id": module_id, "deleted": False})
                if not doc:
                    return {
                        "statusCode": 404,
                        "body": json.dumps({"error": "Documento no encontrado o fue eliminado"})
                    }

                return {
                    "statusCode": 200,
                    "body": json.dumps(doc)
                }
            except Exception as e:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": f"Error al buscar el documento: {str(e)}"})
                }
        items_cursor = collection.find({"deleted": False})
        items = []
        for doc in items_cursor:
            items.append(doc)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "current_page": 1,
                "total_pages": 1,
                "total_items": len(items),
                "per_page": len(items),
                "next_page": None,
                "previous_page": None,
                "items": items
            })
        }
    except Exception as e:
            return _response(400, {"error": f"Error al buscar el documento: {str(e)}"})
  
