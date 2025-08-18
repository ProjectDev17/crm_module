import json
import os
from uuid import uuid4
from datetime import datetime, timezone

from services.db import get_database
from middleware.auth_middleware import auth_middleware
from pymongo.errors import DuplicateKeyError

# === Configuración ===
# DB maestra donde se indexan los tenants (una sola por plataforma)
MASTER_DB_NAME = os.getenv("MASTER_DB_NAME", "crm_master")
TENANT_DB_PREFIX = os.getenv("TENANT_DB_PREFIX", "tenant_")  # ej: tenant_imse_3456

# --- Utilidades ---
def now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())

def norm(s: str | None) -> str:
    return (s or "").strip()

def slugify(name: str) -> str:
    s = norm(name).lower()
    rep = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ñ": "n"
    }
    for a, b in rep.items():
        s = s.replace(a, b)
    return "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in s.replace(" ", "_"))

def col_nit_digits(nit: str) -> str:
    # deja solo dígitos
    return "".join(ch for ch in nit if ch.isdigit())

def compute_dv(nit_digits: str) -> int:
    """
    DV para NIT Colombia (DIAN) – método ponderado tradicional.
    Retorna -1 si no se puede calcular.
    """
    if not nit_digits.isdigit():
        return -1
    weights = [71,67,59,53,47,43,41,37,29,23,19,17,13,7,3]  # soporta hasta 15 dígitos
    nit_rev = nit_digits[::-1]
    total = 0
    for i, ch in enumerate(nit_rev):
        if i >= len(weights):
            break
        total += int(ch) * weights[i]
    dv = total % 11
    if dv > 1:
        dv = 11 - dv
    return dv

def validate_basic_company(payload: dict) -> tuple[bool, str]:
    required = ["name", "nit", "email", "phone", "address", "city"]
    missing = [k for k in required if not norm(payload.get(k))]
    if missing:
        return False, f"Faltan campos obligatorios: {', '.join(missing)}"

    nit_in = norm(payload["nit"])
    digits = col_nit_digits(nit_in)
    if len(digits) < 5:  # longitud mínima razonable
        return False, "NIT inválido"

    dv_calc = compute_dv(digits)
    # si el usuario envía dv explícito, lo validamos; si no, lo inferimos
    input_dv = payload.get("dv")
    if input_dv is not None:
        try:
            input_dv = int(str(input_dv))
        except ValueError:
            return False, "DV inválido"
        if dv_calc != -1 and input_dv != dv_calc:
            return False, f"DV no coincide con el NIT (esperado {dv_calc})"

    return True, ""

def truncate_db_name(name: str, max_bytes: int = 38) -> str:
    """
    Recorta 'name' a 'max_bytes' (en bytes). 
    Si no excede, lo devuelve igual. Respeta UTF-8.
    """
    data = name.encode("utf-8")
    if len(data) <= max_bytes:
        return name
    return data[:max_bytes].decode("utf-8", "ignore")

# --- Handler ---
@auth_middleware
def lambda_handler(event, context):
    """
    POST /onboarding
    Crea el tenant a partir de la información básica de la empresa en Colombia.
    Body esperado (JSON):
    {
      "company": {
        "name": "Sonrisa Dental IPS",
        "nit": "900123456-7",      // se acepta con o sin guion
        "dv": 7,                   // opcional, si no viene se calcula
        "email": "info@...",
        "phone": "+57 3001234567",
        "address": "Cra 10 # 20-30",
        "city": "Medellín",
        "department": "Antioquia", // opcional
        "country": "CO"            // por defecto "CO"
      }
    }
    Respuesta: tenant creado o retornado (idempotente).
    """
    try:
        # Normaliza body
        body_raw = event.get("body") or "{}"
        body = json.loads(body_raw) if isinstance(body_raw, str) else (body_raw or {})
        company = (body.get("company") or {})

        # Validación básica Colombia
        ok, err = validate_basic_company(company)
        if not ok:
            return {"statusCode": 400, "body": json.dumps({"error": err})}

        name = norm(company["name"])
        nit_raw = norm(company["nit"])
        nit_digits = col_nit_digits(nit_raw)
        dv = company.get("dv")
        if dv is None:
            dv = compute_dv(nit_digits)
        country = norm(company.get("country") or "CO")

        # Preparar slug y nombre de DB del tenant
        tenant_slug = slugify(name)  # ej: "sonrisa_dental_ips"
        user_id=event.get("auth_result", {}).get("user_id")
        if not user_id:
            return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized"})}
        tenant_db_name = truncate_db_name(f"{TENANT_DB_PREFIX}{user_id}_{tenant_slug}")  # ej: user_id+tenant_slug

        ts = now_ts()

        # === 1) Registrar/Upsert en DB maestra ===
        master = get_database(MASTER_DB_NAME)
        tenants = master.tenants
        tenants.create_index("nit_digits", unique=True, sparse=True)
        tenants.create_index("tenant_db", unique=True)

        tenant_doc = {
            "$setOnInsert": {
                "_id": str(uuid4()),
                "created_at": ts
            },
            "$set": {
                "name": name,
                "nit": nit_raw,
                "nit_digits": nit_digits,
                "dv": dv,
                "email": norm(company["email"]),
                "phone": norm(company["phone"]),
                "address": norm(company["address"]),
                "city": norm(company["city"]),
                "department": norm(company.get("department")),
                "country": country,
                "tenant_slug": tenant_slug,
                "tenant_db": tenant_db_name,
                "status": "active",
                "updated_at": ts,
                "deleted": False
            }
        }

        tenants.update_one({"nit_digits": nit_digits}, tenant_doc, upsert=True)
        tenant = tenants.find_one({"nit_digits": nit_digits})

        # === 2) Provisionar DB del tenant (colecciones base) ===
        tdb = get_database(tenant_db_name)

        # Colecciones mínimas (solo estructura/base)
        col_company = tdb.company       # 1 doc con datos básicos (reflejo)
        col_settings = tdb.settings     # se llenará después con agenda/facturación/comms
        col_users = tdb.users           # se llenará después
        col_patients = tdb.patients     # se llenará después
        col_services = tdb.services     # se llenará después
        col_appointments = tdb.appointments  # se llenará después

        # Índices mínimos
        col_company.create_index("nit_digits", unique=True)
        col_users.create_index([("email", 1)], unique=False, sparse=True)
        col_patients.create_index([("document", 1), ("type", 1)], unique=False, sparse=True)
        col_services.create_index([("code", 1)], unique=True, sparse=True)
        col_appointments.create_index([("date", 1), ("professional_id", 1)])

        # Upsert de la compañía en la DB del tenant (reflex de lo básico)
        col_company.update_one(
            {"nit_digits": nit_digits},
            {
                "$setOnInsert": {"_id": str(uuid4()), "created_at": ts},
                "$set": {
                    "name": name,
                    "nit": nit_raw,
                    "nit_digits": nit_digits,
                    "dv": dv,
                    "email": norm(company["email"]),
                    "phone": norm(company["phone"]),
                    "address": norm(company["address"]),
                    "city": norm(company["city"]),
                    "department": norm(company.get("department")),
                    "country": country,
                    "updated_at": ts,
                    "deleted": False
                }
            },
            upsert=True
        )

        return {
            "statusCode": 201,
            "body": json.dumps({
                "message": "Tenant creado/provisionado correctamente",
                "tenant": {
                    "id": tenant["_id"],
                    "name": tenant["name"],
                    "nit": tenant["nit"],
                    "dv": tenant.get("dv"),
                    "tenant_db": tenant["tenant_db"],
                    "tenant_slug": tenant["tenant_slug"],
                    "status": tenant["status"]
                },
                "collections": {
                    "company": col_company.name,
                    "settings": col_settings.name,
                    "users": col_users.name,
                    "patients": col_patients.name,
                    "services": col_services.name,
                    "appointments": col_appointments.name
                }
            })
        }

    except DuplicateKeyError as dke:
        return {"statusCode": 409, "body": json.dumps({"error": "Tenant duplicado", "detail": str(dke)})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
