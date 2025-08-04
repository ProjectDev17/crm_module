# src/middleware/auth_middleware.py

import os
import json
import logging
import jwt
import urllib.request
from jwt import ExpiredSignatureError, InvalidTokenError
from functools import wraps

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cargamos el JWKS local si lo estás usando, o configuramos el PyJWKClient
_JWKS_CLIENT = None
_COGNITO_ISSUER = None

def _initialize_jwks_client():
    global _JWKS_CLIENT, _COGNITO_ISSUER

    region = os.getenv("AWS_REGION")
    user_pool_id = os.getenv("COGNITO_USER_POOL_ID")
    logger.info(f"[auth] Inicializando JWKS Client con AWS_REGION={region} y COGNITO_USER_POOL_ID={user_pool_id}")
    if not region or not user_pool_id:
        raise RuntimeError("Debes definir AWS_REGION y COGNITO_USER_POOL_ID en el entorno")

    issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
    jwks_url = f"{issuer}/.well-known/jwks.json"
    logger.info(f"[auth] JWKS URL: {jwks_url}")

    _JWKS_CLIENT = jwt.PyJWKClient(jwks_url)
    _COGNITO_ISSUER = issuer

def auth_middleware(func):
    @wraps(func)
    def wrapper(event, context, *args, **kwargs):
        try:
            # Inicializar cliente JWKS si no existe
            global _JWKS_CLIENT, _COGNITO_ISSUER
            if _JWKS_CLIENT is None:
                _initialize_jwks_client()

            headers = event.get("headers") or {}
            auth_header = headers.get("Authorization") or headers.get("authorization")
            logger.info(f"[auth] Headers recibidos: {headers.keys()}")
            if not auth_header:
                logger.warning("[auth] Falta header Authorization")
                return {"statusCode": 401, "body": json.dumps({"message": "Authorization header missing"})}

            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                logger.warning(f"[auth] Formato inválido de Authorization header: {auth_header}")
                return {"statusCode": 401, "body": json.dumps({"message": "Invalid Authorization header format"})}

            token = parts[1]
            logger.info(f"[auth] Token recibido (truncado): {token[:10]}...")

            # Intentar obtener la clave pública y decodificar
            signing_key = _JWKS_CLIENT.get_signing_key_from_jwt(token).key
            logger.info("[auth] Clave pública obtenida; procediendo a decodificar JWT")

            decoded = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                issuer=_COGNITO_ISSUER
            )
            logger.info(f"[auth] JWT decodificado con éxito. Claims: {list(decoded.keys())}")

            # Inyectar claims en event
            event["requestContext"] = event.get("requestContext", {})
            event["requestContext"]["authorizer"] = decoded
            return func(event, context, *args, **kwargs)

        except ExpiredSignatureError:
            logger.warning("[auth] Token expirado")
            return {"statusCode": 401, "body": json.dumps({"message": "Token expired"})}
        except InvalidTokenError as e:
            logger.warning(f"[auth] Token inválido: {str(e)}")
            return {"statusCode": 401, "body": json.dumps({"message": f"Invalid token: {str(e)}"})}
        except Exception as e:
            # Loguear el stack completo para ver la causa exacta
            logger.error("[auth] Error inesperado validando JWT", exc_info=True)
            return {"statusCode": 500, "body": json.dumps({"message": f"Error validating token: {str(e)}"})}

    return wrapper
