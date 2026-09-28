from __future__ import annotations


SENSITIVE_TERMS = {
    "login",
    "log in",
    "sign in",
    "iniciar sesión",
    "submit",
    "send",
    "enviar",
    "publish",
    "publicar",
    "buy",
    "purchase",
    "comprar",
    "checkout",
    "pay",
    "pagar",
    "delete",
    "eliminar",
    "accept terms",
    "aceptar términos",
    "password",
    "contraseña",
    "credit card",
    "tarjeta de crédito",
    "upload",
    "subir archivo",
}


def sensitive_reason(action: str, arguments: dict) -> str | None:
    if bool(arguments.get("sensitive")):
        return str(arguments.get("reason") or "La acción fue marcada como sensible")
    combined = " ".join(str(value).lower() for value in arguments.values())
    if action == "type" and any(
        marker in combined for marker in ("password", "email", "tel", "credit", "card")
    ):
        return "El agente quiere introducir datos en un campo potencialmente sensible"
    if action == "click":
        for term in SENSITIVE_TERMS:
            if term in combined:
                return f"El destino del clic parece sensible: {term}"
    return None

