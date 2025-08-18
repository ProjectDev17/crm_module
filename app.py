# app.py

import os
import json



# 2) Importa tus sub‐handlers
from handlers.handle_get    import lambda_handler as get_handler
from handlers.handle_post   import lambda_handler as post_handler
from handlers.handle_put    import lambda_handler as put_handler
from handlers.handle_delete import lambda_handler as delete_handler

from handlers_pubilc.handle_post import lambda_handler as public_post_handler

def lambda_handler(event, context):
    """
    2) Obtiene MONGODB_DB_NAME de entorno (ya definido en template.yaml).
    3) Inyecta db_name en event y despacha según HTTP method.
    """
    # 1. Leer la variable de entorno (definida en template.yaml)
    db_name = os.getenv("MONGODB_DB_NAME")
    if not db_name:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "No se encontró la variable de entorno MONGODB_DB_NAME"
            })
        }

    # 2. Inyectar db_name en event para que los sub‐handlers puedan usarla
    event["db_name"] = db_name

    # 3. Detectar método HTTP (REST API v1 vs HTTP API v2)
    method = event.get("httpMethod")
    path = event.get("path") \
        or event.get("rawPath") \
        or event.get("requestContext", {}).get("http", {}).get("path", "")

    if method is None:
        method = event.get("requestContext", {}) \
                      .get("http", {}) \
                      .get("method", "")
    method = method.upper()

    try:
        print(f"Processing {method} request for {path}")
        #si el path contiene /public, usa el handler público
        if "/public" in path:
            if method == "POST":
                return public_post_handler(event, context)
            else:
                return {
                    "statusCode": 405,
                    "body": json.dumps({
                        "error": f"Método {method} no soportado para la ruta {path}"
                    })
                }
        if method == "GET":
            return get_handler(event, context)

        elif method == "POST":
            return post_handler(event, context)

        elif method == "PUT":
            return put_handler(event, context)

        elif method == "DELETE":
            return delete_handler(event, context)

        else:
            return {
                "statusCode": 405,
                "body": json.dumps({
                    "error": f"Método {method} no soportado para la ruta {path}"
                })
            }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
