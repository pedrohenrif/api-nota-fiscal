from __future__ import annotations

ERRO_TIPOS = (
    "sem_depara",
    "sem_lote",
    "sem_fornecedor",
    "conta_contabil",
    "retorno_pr",
    "timeout_pr",
    "outro",
)


def classify_error_tipo(message: str | None) -> str | None:
    if not message or not str(message).strip():
        return None

    text = str(message).casefold()

    if any(
        token in text
        for token in (
            "timed out",
            "timeout",
            "readtimeout",
            "connecttimeout",
            "circuit breaker",
            "execution timeout",
            "timeout expired",
            "timeout period elapsed",
        )
    ):
        return "timeout_pr"

    if any(
        token in text
        for token in (
            "conta contabil",
            "conta contábil",
            "contacontabil",
            "plano de contas",
            "conta cont",
        )
    ):
        return "conta_contabil"

    if any(
        token in text
        for token in (
            "sem fornecedor",
            "fornecedor nao",
            "fornecedor não",
            "fornecedor invalido",
            "fornecedor inválido",
            "fornecedor nao cadastrado",
            "fornecedor não cadastrado",
            "cnpj nao",
            "cnpj não",
            "cnpj invalido",
            "cnpj inválido",
            "cnpj do emitente",
            "emitente nao",
            "emitente não",
        )
    ):
        return "sem_fornecedor"

    if any(
        token in text
        for token in (
            "de-para",
            "depara",
            "sem vinculo",
            "sem vínculo",
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
