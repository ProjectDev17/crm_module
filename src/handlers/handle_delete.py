import json
from datetime import datetime

from services.db import get_database
from middleware.auth_middleware import auth_middleware

@auth_middleware
def lambda_handler(event, context):
    """
    Lógica para DELETE  /templates/{id} (borrado lógico).
    Cambia el campo 'deleted' a True y actualiza 'updated_at' y 'updated_by'.
    """
    try:
        # 1. Obtener el nombre de la base
        db_name = event.get("db_name")
        if not db_name:
            return _response(500, {"error": "No se recibió db_name en el evento"})

        # 2. Conectar a la base
        db = get_database(db_name)
        template_id = event.get("pathParameters", {}).get("id")
        table_name = event.get("queryStringParameters", {}).get("table_name")
        #valida si viene el table_name
        if not table_name:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Falta el campo 'table_name' en el cuerpo de la solicitud"})
            }
        collection = db[table_name]

        # 3. Leer el ID de la plantilla

        if not template_id:
            return _response(400, {"error": "Falta el parámetro 'id'"})

        # 4. Obtener usuario desde token (sub)
        auth_result = event.get("auth_result", {})
        user_data = auth_result.get("user_data", {})
        updated_by = user_data.get("sub") or "unknown"

        # 5. Actualizar documento: borrado lógico
        result = collection.update_one(
            {"_id": template_id},
            {
                "$set": {
                    "deleted": True,
                    "updated_at": int(datetime.now().timestamp()),
                    "updated_by": updated_by
                }
            }
        )

        if result.matched_count == 0:
            return _response(404, {"error": "No se encontró la plantilla con ese ID para eliminar"})

        return _response(200, {"message": f"Plantilla {template_id} marcada como eliminada"})

    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "body": json.dumps(body_dict)
    }
