# handlers/handle_get.py
import os
import json
from services.db import get_database
from pymongo.errors import ServerSelectionTimeoutError
from middleware.auth_middleware import auth_middleware

@auth_middleware
def lambda_handler(event, context):
    """
    Lógica para GET /templates o GET /templates/{id}.
    - Si se pasa {id}, devuelve un solo documento (si deleted == false).
    - Si no se pasa, devuelve todos los no eliminados (deleted == false).
    """
    try:
        db_name = event.get("db_name")
        if not db_name:
            return _response(500, {"error": "No se recibió db_name en el evento"})

        try:
            db = get_database(db_name)
        except ValueError as ve:
            return _response(500, {"error": str(ve)})
        except ServerSelectionTimeoutError as err:
            return _response(502, {"error": f"No se pudo conectar a MongoDB: {err}"})
        
        template_id = event.get("pathParameters", {}).get("id")
        table_name = event.get("queryStringParameters", {}).get("table_name")
        #valida si viene el table_name
        if not table_name:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Falta el campo 'table_name' en el cuerpo de la solicitud"})
            }

        collection = db[table_name]

        # 🔹 GET /templates/{id}
        if template_id:
            try:
                doc = collection.find_one({"_id": template_id, "deleted": False})
                if not doc:
                    return _response(404, {"error": "Documento no encontrado o fue eliminado"})

                _normalize_doc(doc)
                return _response(200, {
                    "message": "Item encontrado correctamente",
                    "item": doc
                })
            except Exception as e:
                return _response(400, {"error": f"Error al buscar el documento: {str(e)}"})

        # 🔹 GET /templates
        items_cursor = collection.find({"deleted": False})
        items = []
        for doc in items_cursor:
            _normalize_doc(doc)
            items.append(doc)

        return _response(200, {
            "current_page": 1,
            "total_pages": 1,
            "total_items": len(items),
            "per_page": len(items),
            "next_page": None,
            "previous_page": None,
            "items": items
        })

    except Exception as e:
        return _response(500, {"error": str(e)})


def _normalize_doc(doc):
    """Convierte ObjectId y timestamps para serialización JSON."""
    doc["_id"] = str(doc["_id"])
    if "created_at" in doc:
        doc["created_at"] = (
            doc["created_at"].isoformat()
            if hasattr(doc["created_at"], "isoformat")
            else str(doc["created_at"])
        )
    if "updated_at" in doc:
        doc["updated_at"] = (
            doc["updated_at"].isoformat()
            if hasattr(doc["updated_at"], "isoformat")
            else str(doc["updated_at"])
        )


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "body": json.dumps(body_dict)
    }
