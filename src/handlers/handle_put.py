import json
from datetime import datetime
from src.services.db import get_database
from src.middleware.auth_middleware import auth_middleware

@auth_middleware
def lambda_handler(event, context):
    """
    Lógica para PUT /templates/{id}:
    - Actualiza campos editables desde el body
    - Verifica que el documento no esté marcado como deleted
    - Mantiene el tracking con updated_at y updated_by
    """
    try:
        # 1. Leer el nombre de la base
        db_name = event.get("db_name")
        if not db_name:
            return _response(500, {"error": "No se recibió db_name en el evento"})

        # 2. Extraer usuario autenticado desde Cognito
        auth_result = event.get("auth_result", {})
        user_data = auth_result.get("user_data", {})
        updated_by = user_data.get("sub") or "unknown"

        # 3. Leer ID desde pathParameters
        template_id = event.get("pathParameters", {}).get("id")
        if not template_id:
            return _response(400, {"error": "Falta el parámetro 'id' en la ruta"})

        # 4. Parsear body como payload
        payload = json.loads(event.get("body") or "{}")
        if not payload or not isinstance(payload, dict):
            return _response(400, {"error": "El body debe ser un JSON válido con campos a actualizar"})

        # 5. Conectar a la DB
        db = get_database(db_name)
        body = json.loads(event.get("body") or "{}")
        table_name = body.get("table_name")
        #valida si viene el table_name
        if not table_name:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Falta el campo 'table_name' en el cuerpo de la solicitud"})
            }
        collection = db[table_name]

        # 6. Verificar existencia y que no esté eliminado
        existing_doc = collection.find_one({"_id": template_id})
        if not existing_doc:
            return _response(404, {"error": "Plantilla no encontrada"})
        if existing_doc.get("deleted", False):
            return _response(400, {"error": "No se puede editar una plantilla eliminada"})

        # 7. Validar nombre duplicado si incluye "name"
        new_name = payload.get("name")
        if new_name and isinstance(new_name, str) and new_name.strip():
            new_name = new_name.strip()
            if collection.find_one({
                "name": {"$regex": f"^{new_name}$", "$options": "i"},
                "_id": {"$ne": template_id},
                "deleted": False
            }):
                return _response(409, {"error": f"Ya existe otra plantilla con el nombre '{new_name}'"})
            payload["name"] = new_name

        # 8. Preparar y aplicar la actualización
        payload["updated_at"] = int(datetime.now().timestamp())
        payload["updated_by"] = updated_by

        result = collection.update_one(
            {"_id": template_id},
            {"$set": payload}
        )

        if result.matched_count == 0:
            return _response(404, {"error": "No se encontró la plantilla con ese ID"})

        updated_doc = collection.find_one({"_id": template_id})
        updated_doc["_id"] = str(updated_doc["_id"])

        return _response(200, {
            "message": f"Plantilla {template_id} actualizada correctamente",
            "item": updated_doc
        })

    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "body": json.dumps(body_dict)
    }
