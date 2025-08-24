import json
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

        _id = event.get("pathParameters", {}).get("id")
        if not _id:
            return _response(400, {"error": "Falta el parámetro '_id' en la ruta"})

        # Verificar existencia y que no esté eliminado
        existing_doc = collection.find_one({"_id": _id})
        if not existing_doc:
            return _response(404, {"error": f"No se encontró {table_name} con ID {_id}"})
        if existing_doc.get("deleted", False):
            return _response(400, {"error": f"No se puede editar {table_name} con ID {_id} porque está eliminado"})

        # Validar nombre duplicado si incluye "name"
        new_name = body.get("name")
        if new_name and isinstance(new_name, str) and new_name.strip():
            new_name = new_name.strip()
            if collection.find_one({
                "name": {"$regex": f"^{new_name}$", "$options": "i"},
                "_id": {"$ne": _id},
                "deleted": False
            }):
                return _response(409, {"error": f"Ya existe otra {table_name} con el nombre '{new_name}'"})
            body["name"] = new_name

        # Preparar y aplicar la actualización
        body["updated_at"] = int(datetime.now().timestamp())
        body["updated_by"] = user_data.get("_id")

        result = collection.update_one(
            {"_id": _id},
            {"$set": body}
        )

        if result.matched_count == 0:
            return _response(404, {"error": f"No se encontró {table_name} con ID {_id}"})

        updated_doc = collection.find_one({"_id": _id})
        updated_doc["_id"] = str(updated_doc["_id"])

        return _response(200, {
            "message": f"{table_name} {_id} actualizada correctamente",
            "item": updated_doc
        })

    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "body": json.dumps(body_dict)
    }
