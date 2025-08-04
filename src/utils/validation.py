
import re

# Expresión regular para validar UUID
UUID_REGEX = re.compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')

def is_valid_uuid(uuid_str):
    """Verifica si una cadena es un UUID válido."""
    return bool(UUID_REGEX.match(uuid_str))
