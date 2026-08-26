from __future__ import annotations

ERRO_TIPOS = ("sem_depara", "sem_lote", "retorno_pr", "outro")


def classify_error_tipo(message: str | None) -> str | None:
    if not message or not str(message).strip():
        return None

    text = str(message).lower()

    if any(
        token in text
        for token in (
            "de-para",
            "depara",
            "sem vinculo",
            "vazio no pr",
            "nao possui vinculo",
            "não possui vínculo",
        )
    ):
        return "sem_depara"

    if any(
        token in text
        for token in (
            "sem lote",
            "necessidade de lote",
            "lotenf",
            "controle de lote",
            "controledelote",
            "observacao field is required",
        )
    ) or ("lote" in text and "obrigat" in text):
        return "sem_lote"

    if any(
        token in text
        for token in (
            "pr http",
            "pr:",
            "materias.dbo.produto",
            "ja integrada",
            "já integrada",
            "produto informado",
            "datetime",
            "validade",
        )
    ):
        return "retorno_pr"

    if "lote" in text:
        return "sem_lote"

    return "outro"
