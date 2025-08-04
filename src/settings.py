# src/settings.py

"""
Aquí definimos los permisos requeridos para cada recurso y verbo HTTP.
Puedes ajustar este diccionario según las necesidades de tu aplicación.
"""

PERMISSION_REQUIRED = {
    # Recurso “templates”:
    "templates": {
        "GET":    ["read:templates"],
        "POST":   ["create:templates"],
        "PUT":    ["update:templates"],
        "DELETE": ["delete:templates"]
    },
}
