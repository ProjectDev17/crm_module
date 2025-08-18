# app.py

import os
import json

# Handlers públicos
from handlers.handle_get    import lambda_handler as handle_get
from handlers.handle_post   import lambda_handler as handle_post
from handlers.handle_put    import lambda_handler as handle_put
from handlers.handle_delete import lambda_handler as handle_delete
from handlers_pubilc.handle_post import lambda_handler as public_handle_post
from handlers.handle_onboarding import lambda_handler as handle_onboarding

def lambda_handler(event, context):
    db_name = os.getenv("MONGODB_DB_NAME")
    if not db_name:
        return _response(500, {"error": "No se encontró la variable de entorno MONGODB_DB_NAME"})

    event["db_name"] = db_name

    method = _get_http_method(event)
    path = _get_path(event)

    try:
        print(f"Processing {method} request for {path}")
        if "/public" in path:
            if method == "POST":
                return public_handle_post(event, context)
            else:
                return {
                    "statusCode": 405,
                    "body": json.dumps({
                        "error": f"Método {method} no soportado para la ruta {path}"
                    })
                }
        elif "/onboarding" in path:
            if method == "POST":
                return handle_onboarding(event, context)
        elif "/modules" in path:
            if method == "GET":
                return handle_get(event, context)

            elif method == "POST":
                return handle_post(event, context)

            elif method == "PUT":
                return put_handler(event, context)

            elif method == "DELETE":
                return delete_handler(event, context)

        
        
        return _response(405, {"error": f"Método {method} no soportado para {path}"})

    except Exception as e:
        return _response(500, {"error": str(e)})

# Helpers
def _get_http_method(event):
    m = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method", "")
    return m.upper()

def _get_path(event):
    return event.get("path") or event.get("rawPath") or event.get("requestContext", {}).get("http", {}).get("path", "")

def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }
