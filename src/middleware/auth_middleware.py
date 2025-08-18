# middleware/auth_middleware.py
import os
import json
from typing import Any, Callable, Dict
from services.token_service import decode_token
from services.db import get_database

try:
    from bson import ObjectId
except Exception:
    ObjectId = None  # si no está en la layer, no rompemos

def _get_header(headers: Dict[str, str], name: str, default: str = "") -> str:
    if not isinstance(headers, dict):
        return default
    # maneja mayúsculas/minúsculas de API Gateway/ALB
    return headers.get(name) or headers.get(name.lower()) or headers.get(name.capitalize()) or default

def authenticate_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """Valida el token y retorna {'statusCode': 200, 'user_id': ..., 'user_data': ...} o un error."""
    headers = event.get("headers", {}) if isinstance(event, dict) else {}
    auth_header = _get_header(headers, "authorization", "")

    if not auth_header.startswith("Bearer "):
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid token format"})}

    access_token = auth_header.split(" ", 1)[1].strip()
    if not access_token:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing access token"})}

    decoded_token = decode_token(access_token)
    if not decoded_token:
        return {"statusCode": 401, "body": json.dumps({"error": "Invalid access token"})}
    if isinstance(decoded_token, dict) and "statusCode" in decoded_token and decoded_token["statusCode"] != 200:
        # si tu decode_token ya devuelve errores con statusCode
        return decoded_token

    # intenta obtener el user_id con distintos esquemas de payload
    user_id = (
        (decoded_token.get("user") or {}).get("_id")
        if isinstance(decoded_token, dict) else None
    ) or (decoded_token.get("sub") if isinstance(decoded_token, dict) else None)

    if not user_id:
        return {"statusCode": 401, "body": json.dumps({"error": "Invalid token: missing user_id"})}

    # db_name desde el evento o variable de entorno
    db_name = (event.get("db_name") if isinstance(event, dict) else None) or os.getenv("MONGODB_DB_NAME")
    if not db_name:
        return {"statusCode": 500, "body": json.dumps({"error": "Missing DB name (MONGODB_DB_NAME)"})}

    db = get_database(db_name)
    users = db["users"]

    # si el _id es ObjectId válido, úsalo; si no, búscalo como string
    query_id = None
    if ObjectId and isinstance(user_id, str) and ObjectId.is_valid(user_id):
        query_id = ObjectId(user_id)
    else:
        query_id = user_id

    user_data = users.find_one({"_id": query_id})
    if not user_data:
        return {"statusCode": 404, "body": json.dumps({"error": "User not found"})}

    # valida que el token corresponda al actual guardado
    current_access_token = user_data.get("current_access_token")
    if not current_access_token or access_token != current_access_token:
        return {"statusCode": 401, "body": json.dumps({"error": "Invalid token"})}

    return {
        "statusCode": 200,
        "user_id": str(user_data.get("_id")),
        "user_data": user_data,  # si es sensible, evita devolver todo
        "access_token": access_token,
    }

def auth_middleware(handler: Callable[[Dict[str, Any], Any], Dict[str, Any]]):
    """Decorador correcto: valida y, si todo ok, inyecta auth_result en event."""
    def wrapper(event: Dict[str, Any], context: Any, *args, **kwargs):
        result = authenticate_request(event)
        if not isinstance(result, dict) or result.get("statusCode") != 200:
            # retorna el error tal cual
            return result

        # inyecta auth_result al event para uso posterior
        if not isinstance(event, dict):
            new_event = {}
        else:
            new_event = dict(event)  # copia superficial
        new_event["auth_result"] = result
        return handler(new_event, context, *args, **kwargs)
    return wrapper
