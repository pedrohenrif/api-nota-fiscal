import httpx
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from services.web_api import panel_data, repository
from services.common.estab_config import (
    ensure_estab_config_table,
    get_estab_config,
    list_estab_configs,
    update_estab_config,
)
from services.common.report_recipients import (
    create_recipient,
    delete_recipient,
    ensure_report_recipients_table,
    list_recipients,
    update_recipient,
)
from services.web_api.audit import (
    client_ip,
    list_access_logs,
    resolve_action,
    should_skip_path,
    username_from_request,
    write_audit_log,
)
from services.web_api.config import (
    BOOTSTRAP_ADMIN_PASSWORD,
    BOOTSTRAP_ADMIN_USERNAME,
    CORS_ORIGINS,
    ESTABELECIMENTOS,
    EXTRACTOR_URL,
    REPORT_URL,
)
from services.web_api.db import Base, SessionLocal, engine, get_db
from services.web_api.deps import get_current_user, require_admin
from services.web_api.http_errors import raise_for_extractor_response
from services.web_api.models import Usuario
from services.web_api.schemas import (
    AccessAuditPageOut,
    DestinatarioCreate,
    DestinatarioOut,
    DestinatarioUpdate,
    EmitirNotaEspecificaRequest,
    EmitirNotaRequest,
    EnviarRelatorioRequest,
    EstabelecimentoConfigOut,
    EstabelecimentoConfigUpdate,
    LoginRequest,
    NotaConsultaOut,
    NotaDetalheOut,
    NotaStatusOut,
    NotaStatusPageOut,
    ReemitirNotaRequest,
    Token,
    UsuarioCreate,
    UsuarioOut,
)
from services.web_api.security import create_access_token, verify_password
from services.processor.depara import enrich_preview_with_depara

app = FastAPI(title="Web API - Painel NF")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def access_audit_middleware(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if request.method == "OPTIONS" or should_skip_path(path):
        return response
    # Login e tratado no endpoint (sucesso/falha com detalhe).
    if path == "/auth/login":
        return response
    try:
        username, role, estabelecimento = username_from_request(request)
        db = SessionLocal()
        try:
            write_audit_log(
                db,
                ip=client_ip(request),
                method=request.method,
                path=path,
                status_code=response.status_code,
                username=username,
                role=role,
                estabelecimento=estabelecimento,
                action=resolve_action(request.method, path),
                user_agent=request.headers.get("user-agent"),
            )
        finally:
            db.close()
    except Exception:
        pass
    return response


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_estab_config_table()
    ensure_report_recipients_table()
    _seed_admin()


def _seed_admin() -> None:
    db = SessionLocal()
    try:
        if repository.get_user_by_username(db, BOOTSTRAP_ADMIN_USERNAME) is None:
            repository.create_user(
                db,
                username=BOOTSTRAP_ADMIN_USERNAME,
                password=BOOTSTRAP_ADMIN_PASSWORD,
                role="adm",
                estabelecimento=None,
            )
    finally:
        db.close()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "web_api"}


@app.post("/auth/login", response_model=Token)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Token:
    user = repository.get_user_by_username(db, payload.username)
    ip = client_ip(request)
    ua = request.headers.get("user-agent")
    if user is None or not verify_password(payload.password, user.hashed_password):
        try:
            write_audit_log(
                db,
                ip=ip,
                method="POST",
                path="/auth/login",
                status_code=401,
                username=payload.username,
                action="login_falha",
                detail="Usuario ou senha invalidos",
                user_agent=ua,
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario ou senha invalidos",
        )
    token = create_access_token(
        subject=user.username, role=user.role, estabelecimento=user.estabelecimento
    )
    try:
        write_audit_log(
            db,
            ip=ip,
            method="POST",
            path="/auth/login",
            status_code=200,
            username=user.username,
            role=user.role,
            estabelecimento=user.estabelecimento,
            action="login",
            detail="Login OK",
            user_agent=ua,
        )
    except Exception:
        pass
    return Token(access_token=token)


@app.get("/auth/me", response_model=UsuarioOut)
def me(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    return current_user


@app.get("/estabelecimentos", response_model=list[str])
def estabelecimentos(current_user: Usuario = Depends(get_current_user)) -> list[str]:
    if current_user.role == "adm":
        return ESTABELECIMENTOS
    return [current_user.estabelecimento] if current_user.estabelecimento else []


@app.get("/usuarios", response_model=list[UsuarioOut])
def list_usuarios(
    _: Usuario = Depends(require_admin), db: Session = Depends(get_db)
) -> list[Usuario]:
    return repository.list_users(db)


@app.post("/usuarios", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def create_usuario(
    payload: UsuarioCreate,
    _: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Usuario:
    if repository.get_user_by_username(db, payload.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Usuario ja existe"
        )

    if payload.role == "usuario":
        if not payload.estabelecimento:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Estabelecimento e obrigatorio para usuario",
            )
        if payload.estabelecimento not in ESTABELECIMENTOS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Estabelecimento invalido",
            )

    estabelecimento = payload.estabelecimento if payload.role == "usuario" else None
    return repository.create_user(
        db,
        username=payload.username,
        password=payload.password,
        role=payload.role,
        estabelecimento=estabelecimento,
    )


def _resolve_estabelecimento(current_user: Usuario, requested: str | None) -> str:
    if current_user.role == "adm":
        if not requested:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Informe o estabelecimento",
            )
        if requested not in ESTABELECIMENTOS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Estabelecimento invalido",
            )
        return requested

    if not current_user.estabelecimento:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario sem estabelecimento vinculado",
        )
    return current_user.estabelecimento


@app.post("/notas/emitir")
def emitir_nota(
    payload: EmitirNotaRequest,
    current_user: Usuario = Depends(get_current_user),
) -> dict:
    estabelecimento = _resolve_estabelecimento(current_user, payload.estabelecimento)
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{EXTRACTOR_URL}/run", params={"estabelecimento": estabelecimento}
            )
            raise_for_extractor_response(response)
            result = response.json()
    except HTTPException:
        raise
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servico de extracao indisponivel. Tente novamente em instantes.",
        )
    return {"estabelecimento": estabelecimento, "resultado": result}


@app.get("/notas/consultar", response_model=NotaConsultaOut)
def consultar_nota(
    nr_sequencia: str,
    estabelecimento: str | None = None,
    current_user: Usuario = Depends(get_current_user),
) -> dict:
    target = _resolve_estabelecimento(current_user, estabelecimento)
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.get(
                f"{EXTRACTOR_URL}/notas/consultar",
                params={"estabelecimento": target, "nr_sequencia": nr_sequencia},
            )
            raise_for_extractor_response(response)
            return response.json()
    except HTTPException:
        raise
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servico de extracao indisponivel. Tente novamente em instantes.",
        )


@app.post("/notas/emitir-especifica")
def emitir_nota_especifica(
    payload: EmitirNotaEspecificaRequest,
    current_user: Usuario = Depends(get_current_user),
) -> dict:
    target = _resolve_estabelecimento(current_user, payload.estabelecimento)
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{EXTRACTOR_URL}/notas/emitir-especifica",
                params={
                    "estabelecimento": target,
                    "nr_sequencia": payload.nr_sequencia.strip(),
                },
            )
            raise_for_extractor_response(response)
            result = response.json()
    except HTTPException:
        raise
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servico de extracao indisponivel. Tente novamente em instantes.",
        )
    return {"estabelecimento": target, "resultado": result}


REEMITIR_STATUS = frozenset({"retry_pending", "dead_letter"})


def _assert_nota_access(current_user: Usuario, nota: dict) -> None:
    if current_user.role == "adm":
        return
    if nota.get("estabelecimento") != current_user.estabelecimento:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissao para esta nota",
        )


@app.post("/notas/reemitir")
def reemitir_nota(
    payload: ReemitirNotaRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    nota = panel_data.get_nota_by_id(db, payload.id)
    if nota is None:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")

    _assert_nota_access(current_user, nota)

    if nota.get("status") not in REEMITIR_STATUS:
        raise HTTPException(
            status_code=422,
            detail="Reemissao permitida apenas para notas com falha (retry_pending ou dead_letter)",
        )

    nr_sequencia = (nota.get("nr_sequencia") or "").strip()
    if not nr_sequencia:
        raise HTTPException(
            status_code=422,
            detail="Nota sem nr_sequencia — use Emitir nota especifica informando o numero",
        )

    estabelecimento = nota["estabelecimento"]
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{EXTRACTOR_URL}/notas/emitir-especifica",
                params={"estabelecimento": estabelecimento, "nr_sequencia": nr_sequencia},
            )
            raise_for_extractor_response(response)
            result = response.json()
    except HTTPException:
        raise
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servico de extracao indisponivel. Tente novamente em instantes.",
        )

    return {
        "id": payload.id,
        "estabelecimento": estabelecimento,
        "nr_sequencia": nr_sequencia,
        "nf": nota.get("nf"),
        "resultado": result,
    }


@app.get("/notas", response_model=NotaStatusPageOut)
def listar_notas(
    estabelecimento: str | None = None,
    nf: str | None = None,
    nr_sequencia: str | None = None,
    fornecedor: str | None = None,
    status: str | None = None,
    erro_tipo: str | None = None,
    data_nf_inicio: date | None = None,
    data_nf_fim: date | None = None,
    ordenacao: str | None = "nr_sequencia",
    page: int = 1,
    page_size: int = 50,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if current_user.role == "adm":
        target = estabelecimento
    else:
        target = current_user.estabelecimento
    return panel_data.list_notas(
        db,
        estabelecimento=target,
        nf=nf,
        nr_sequencia=nr_sequencia,
        fornecedor=fornecedor,
        status=status,
        erro_tipo=erro_tipo,
        data_nf_inicio=data_nf_inicio,
        data_nf_fim=data_nf_fim,
        ordenacao=ordenacao,
        page=page,
        page_size=page_size,
    )


@app.get("/notas/{nota_id}/detalhe", response_model=NotaDetalheOut)
def detalhe_nota(
    nota_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    nota = panel_data.get_nota_by_id(db, nota_id)
    if nota is None:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")

    _assert_nota_access(current_user, nota)

    detalhe = dict(nota)
    detalhe["cd_operacao_nf"] = None
    detalhe["operacoes_liberadas"] = []
    detalhe["consulta_mensagem"] = None
    detalhe["preview"] = None
    detalhe["depara_resumo"] = None

    nr_sequencia = (nota.get("nr_sequencia") or "").strip()
    if not nr_sequencia:
        detalhe["consulta_mensagem"] = "Nota sem nr_sequencia para consulta no Tasy."
        return detalhe

    estabelecimento = nota["estabelecimento"]
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.get(
                f"{EXTRACTOR_URL}/notas/consultar",
                params={"estabelecimento": estabelecimento, "nr_sequencia": nr_sequencia},
            )
            raise_for_extractor_response(response)
            consulta = response.json()
    except HTTPException as exc:
        detalhe["consulta_mensagem"] = str(exc.detail)
        return detalhe
    except httpx.HTTPError:
        detalhe["consulta_mensagem"] = "Servico de extracao indisponivel."
        return detalhe

    detalhe["cd_operacao_nf"] = consulta.get("cd_operacao_nf")
    detalhe["operacoes_liberadas"] = consulta.get("operacoes_liberadas") or []
    detalhe["preview"] = consulta.get("preview")
    if detalhe["preview"]:
        try:
            preview, resumo = enrich_preview_with_depara(estabelecimento, detalhe["preview"])
            detalhe["preview"] = preview
            detalhe["depara_resumo"] = resumo
        except Exception as exc:
            detalhe["depara_resumo"] = None
            detalhe["consulta_mensagem"] = (
                detalhe.get("consulta_mensagem") or f"Falha ao validar de-para no PR: {exc}"
            )
    if not consulta.get("encontrada"):
        detalhe["consulta_mensagem"] = consulta.get("mensagem") or "Nota nao encontrada no Tasy."
    elif not consulta.get("valido") and not detalhe["preview"]:
        detalhe["consulta_mensagem"] = consulta.get("mensagem") or "Nota sem itens para exibir."

    return detalhe


@app.get("/admin/logs", response_model=NotaStatusPageOut)
def listar_logs(
    _: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
    estabelecimento: str | None = None,
    status: str | None = None,
    erro_tipo: str | None = None,
    somente_erro: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    return panel_data.list_logs(
        db,
        estabelecimento=estabelecimento,
        status=status,
        erro_tipo=erro_tipo,
        somente_erro=somente_erro,
        page=page,
        page_size=page_size,
    )


@app.get("/admin/acesso", response_model=AccessAuditPageOut)
def listar_acesso(
    _: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
    username: str | None = None,
    ip: str | None = None,
    action: str | None = None,
    role: str | None = None,
    estabelecimento: str | None = None,
    status_code: int | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    return list_access_logs(
        db,
        username=username,
        ip=ip,
        action=action,
        role=role,
        estabelecimento=estabelecimento,
        status_code=status_code,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=limit,
        offset=offset,
    )


def _resolve_destinatario_estabelecimento(
    current_user: Usuario, estabelecimento: str | None
) -> str | None:
    if current_user.role == "adm":
        return estabelecimento
    return current_user.estabelecimento


@app.get("/destinatarios", response_model=list[DestinatarioOut])
def listar_destinatarios(
    estabelecimento: str | None = None,
    current_user: Usuario = Depends(get_current_user),
) -> list[dict]:
    target = _resolve_destinatario_estabelecimento(current_user, estabelecimento)
    if current_user.role != "adm" and not target:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario sem estabelecimento vinculado",
        )
    return list_recipients(estabelecimento=target)


@app.post("/destinatarios", response_model=DestinatarioOut, status_code=status.HTTP_201_CREATED)
def criar_destinatario(
    payload: DestinatarioCreate,
    current_user: Usuario = Depends(get_current_user),
) -> dict:
    if current_user.role == "adm":
        target = payload.estabelecimento
        if not target:
            raise HTTPException(status_code=422, detail="Informe o estabelecimento")
    else:
        target = current_user.estabelecimento
        if not target:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario sem estabelecimento vinculado",
            )
        if payload.estabelecimento and payload.estabelecimento != target:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario so pode cadastrar e-mails do proprio estabelecimento",
            )
    try:
        return create_recipient(estabelecimento=target, email=payload.email)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/destinatarios/{recipient_id}", response_model=DestinatarioOut)
def editar_destinatario(
    recipient_id: int,
    payload: DestinatarioUpdate,
    current_user: Usuario = Depends(get_current_user),
) -> dict:
    allowed = None if current_user.role == "adm" else current_user.estabelecimento
    try:
        return update_recipient(
            recipient_id=recipient_id,
            email=payload.email,
            allowed_estabelecimento=allowed,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.delete("/destinatarios/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_destinatario(
    recipient_id: int,
    current_user: Usuario = Depends(get_current_user),
) -> None:
    allowed = None if current_user.role == "adm" else current_user.estabelecimento
    try:
        delete_recipient(
            recipient_id=recipient_id,
            allowed_estabelecimento=allowed,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/admin/estabelecimentos/config", response_model=list[EstabelecimentoConfigOut])
def listar_config_estabelecimentos(_: Usuario = Depends(require_admin)) -> list[dict]:
    return list_estab_configs()


@app.patch(
    "/admin/estabelecimentos/{estabelecimento}/config",
    response_model=EstabelecimentoConfigOut,
)
def atualizar_config_estabelecimento(
    estabelecimento: str,
    payload: EstabelecimentoConfigUpdate,
    _: Usuario = Depends(require_admin),
) -> dict:
    if estabelecimento not in ESTABELECIMENTOS:
        raise HTTPException(status_code=422, detail="Estabelecimento invalido")
    if payload.scheduler_enabled is None and payload.report_enabled is None:
        raise HTTPException(
            status_code=422,
            detail="Informe scheduler_enabled e/ou report_enabled",
        )
    updated = update_estab_config(
        estabelecimento,
        scheduler_enabled=payload.scheduler_enabled,
        report_enabled=payload.report_enabled,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Estabelecimento nao encontrado")
    return updated


@app.post("/admin/relatorios/enviar")
def enviar_relatorio_email(
    payload: EnviarRelatorioRequest,
    _: Usuario = Depends(require_admin),
) -> dict:
    if payload.estabelecimento not in ESTABELECIMENTOS:
        raise HTTPException(status_code=422, detail="Estabelecimento invalido")
    try:
        with httpx.Client(timeout=180.0) as client:
            response = client.post(
                f"{REPORT_URL}/relatorios/enviar",
                params={"estabelecimento": payload.estabelecimento},
            )
            if response.is_error:
                detail = response.text
                try:
                    body = response.json()
                    detail = body.get("detail") or body
                except ValueError:
                    pass
                raise HTTPException(status_code=response.status_code, detail=detail)
            return response.json()
    except HTTPException:
        raise
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servico de relatorio indisponivel. Verifique o report-service.",
        )


@app.get("/admin/estabelecimentos/{estabelecimento}/config", response_model=EstabelecimentoConfigOut)
def obter_config_estabelecimento(
    estabelecimento: str,
    _: Usuario = Depends(require_admin),
) -> dict:
    cfg = get_estab_config(estabelecimento)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Estabelecimento nao encontrado")
    return cfg
