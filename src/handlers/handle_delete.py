import json
from datetime import datetime

from services.db import get_database
from middleware.auth_middleware import auth_middleware

@auth_middleware
def lambda_handler(event, context):
    """
    Lógica para DELETE  (borrado lógico).
    Cambia el campo 'deleted' a True y actualiza 'updated_at' y 'updated_by'.
    """
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

        _id = event.get("pathParameters", {}).get("id")
        if not _id:
            return _response(400, {"error": "Falta el parámetro '_id' en la ruta"})

        # Verificar existencia y que no esté eliminado
        existing_doc = collection.find_one({"_id": _id})
        if not existing_doc:
            return _response(404, {"error": f"No se encontró {table_name} con ID {_id}"})
        if existing_doc.get("deleted", False):
            return _response(400, {"error": f"No se puede editar {table_name} con ID {_id} porque está eliminado"})

        # Actualizar documento: borrado lógico
        result = collection.update_one(
            {"_id": _id},
            {
                "$set": {
                    "deleted": True,
                    "updated_at": int(datetime.now().timestamp()),
                    "updated_by": user_data.get("_id")
                }
            }
        )

        if result.matched_count == 0:
            return _response(404, {"error": f"No se encontró la {table_name} con ese ID para eliminar"})

        return _response(200, {"message": f"{table_name} {_id} marcada como eliminada"})

    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "body": json.dumps(body_dict)
    }
