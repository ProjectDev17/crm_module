# middleware/auth_middleware.py
import os
import json
from typing import Any, Callable, Dict
from services.auth_service import authenticate_request

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
