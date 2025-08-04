# src/services/db.py

from pymongo import MongoClient, errors
import os
import certifi

_client = None

def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        mongo_uri = os.getenv("MONGODB_URI")
        if not mongo_uri:
            raise ValueError("MONGODB_URI is not set in environment variables")

        try:
            _client = MongoClient(
                mongo_uri,
                tls=True,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=5000
            )
            _client.server_info()  # Fuerza conexión inmediata
        except Exception as e:
            raise RuntimeError(f"Error conectando a MongoDB: {str(e)}")

    return _client

def get_database(db_name: str):
    try:
        client = get_mongo_client()
        return client[db_name]
    except Exception as e:
        raise RuntimeError(f"Error obteniendo la base de datos: {str(e)}")
