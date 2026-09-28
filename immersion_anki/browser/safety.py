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
    "download",
    "descargar",
}


def sensitive_reason(action: str, arguments: dict) -> str | None:
    if bool(arguments.get("sensitive")):
        return str(arguments.get("reason") or "La acción fue marcada como sensible")
    combined = " ".join(str(value).lower() for value in arguments.values())
    if action in {"navigate", "new_tab"} and any(
        marker in combined
        for marker in (".exe", ".msi", ".deb", ".rpm", ".appimage", ".dmg", ".pkg")
    ):
        return "La navegación descargaría o abriría un archivo ejecutable"
    if action == "type" and any(
        marker in combined for marker in ("password", "email", "tel", "credit", "card")
    ):
        return "El agente quiere introducir datos en un campo potencialmente sensible"
    if action == "type" and arguments.get("press_enter") and not any(
        marker in combined for marker in ("search", "buscar", "q=")
    ):
        return "Introducir texto y pulsar Enter podría enviar un formulario"
    if action == "click":
        for term in SENSITIVE_TERMS:
            if term in combined:
                return f"El destino del clic parece sensible: {term}"
    return None
