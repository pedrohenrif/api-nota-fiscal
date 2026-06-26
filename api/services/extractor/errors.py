def friendly_oracle_error(exc: Exception) -> str:
    message = str(exc).lower()

    if "oracle_dsn" in message or ("service_name" in message and "invalido" in message):
        return "Configuracao do Oracle invalida. Verifique ORACLE_DSN no servidor."

    if "dpy-3001" in message or "thick mode" in message:
        return (
            "O banco Tasy exige criptografia nativa Oracle (modo thick). "
            "Reconstrua o container do extractor com Oracle Instant Client instalado."
        )

    if "instant client nao encontrado" in message:
        return (
            "Oracle Instant Client nao encontrado no servidor. "
            "Execute: docker compose build extractor-service && docker compose up -d extractor-service"
        )

    if "dpy-6001" in message or "cannot connect" in message or "connection refused" in message:
        return (
            "Nao foi possivel conectar ao banco Tasy. "
            "Verifique rede, firewall e se o servico Oracle esta acessivel a partir da VM."
        )

    if "dpy-4011" in message or "ora-01017" in message or "invalid username/password" in message:
        return "Usuario ou senha do Oracle incorretos (ORACLE_DSN)."

    if "ora-12170" in message or "tns" in message or "timeout" in message:
        return (
            "Tempo esgotado ao conectar no Oracle. "
            "Confirme host, porta e service_name no ORACLE_DSN."
        )

    if "ora-12541" in message or "no listener" in message:
        return "Oracle listener nao encontrado na porta informada."

    if "not found" in message or "ora-00942" in message:
        return "Erro ao consultar tabelas do Tasy. Verifique permissoes do usuario de integracao."

    return (
        "Erro ao consultar o Tasy. Tente novamente ou contate o suporte tecnico "
        "se o problema persistir."
    )
