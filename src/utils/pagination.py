import math
from urllib.parse import urlencode
from src.src.services.db import get_database


def paginate_MongoDB_table(event, table_name: str, db_name: str = "your_database_name"):
    """
    Realiza la paginación de una colección de MongoDB usando parámetros del query string.
    - page: número de página
    - per_page: elementos por página
    - filters: en el futuro puedes extenderlo para más filtros
    """

    db = get_database(db_name)
    collection = db[table_name]

    # Obtener parámetros de la query string
    params = event.get("queryStringParameters") or {}

    try:
        page = int(params.get("page", 1))
        per_page = int(params.get("per_page", 10))
    except ValueError:
        page = 1
        per_page = 10

    if page < 1:
        page = 1

    if per_page < 1:
        per_page = 10

    # Filtro básico: no eliminados
    filters = {"deleted": {"$in": [0, False]}}

    # Conteo total
    total_count = collection.count_documents(filters)

    # Datos paginados
    skip = (page - 1) * per_page
    results_cursor = collection.find(filters).skip(skip).limit(per_page)
    results = list(results_cursor)

    # Construir URL de "next" si hay más resultados
    next_page_url = None
    if (page * per_page) < total_count:
        query_params = {**params, "page": page + 1, "per_page": per_page}
        next_page_url = f"?{urlencode(query_params)}"

    return {
        "count": total_count,
        "results": results,
        "next": next_page_url
    }
