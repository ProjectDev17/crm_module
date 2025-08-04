def validate_data(data):
    if not data.get("name"):
        return False, "Campo 'name' requerido"
    return True, ""
