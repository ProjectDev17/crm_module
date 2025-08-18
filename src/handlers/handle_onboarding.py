import json
from datetime import datetime

from services.db import get_database
from middleware.auth_middleware import auth_middleware

@auth_middleware
def lambda_handler(event, context):
    """
    Lógica para Crear la base de datos y la información inicial.
    """
    try:
        db_name = event.get("db_name")
        if not db_name:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "No se recibió db_name en el evento"})
            }

        db = get_database(db_name)

        # Crear la colección de plantillas
        db.create_collection("templates")

        # Insertar información inicial
        initial_templates = [
            {
                "_id": str(uuid4()),
                "name": "Plantilla 1",
                "description": "Descripción de la plantilla 1",
                "created_at": int(datetime.now().timestamp()),
                "updated_at": int(datetime.now().timestamp()),
                "deleted": False
            },
            {
                "_id": str(uuid4()),
                "name": "Plantilla 2",
                "description": "Descripción de la plantilla 2",
                "created_at": int(datetime.now().timestamp()),
                "updated_at": int(datetime.now().timestamp()),
                "deleted": False
            }
        ]

        db.templates.insert_many(initial_templates)

        return {
            "statusCode": 201,
            "body": json.dumps({"message": "Base de datos y plantillas iniciales creadas"})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
