
import jwt
import os
import json

SECRET_KEY = os.getenv('SECRET_KEY')

def decode_token(access_token):
    try:
        # Decodificar el token para obtener el payload (incluye user_id y otros datos)
        decoded_token = jwt.decode(access_token, SECRET_KEY, algorithms=['HS256'])  # Ajusta el algoritmo si usas otro
        return decoded_token
    except jwt.ExpiredSignatureError:
        # El token ha expirado
        return {
            "statusCode": 401,
            "body": json.dumps({"message": "Token has expired"})
        }
        
    except jwt.InvalidTokenError:
        # Token inválido (firma incorrecta, formato inválido, etc.)
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid token."})
        }
    except Exception as e:
        print(str(e), 'decode_token')
        # Otros errores inesperados
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Error decoding token: {str(e)}"})
        }
