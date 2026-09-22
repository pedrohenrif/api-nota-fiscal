import csv
import io
from datetime import date, datetime

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
    ensure_report_recipients_table,
    list_recipients,
    update_recipient,
)
from services.web_api.audit import (
    client_ip,
    list_access_logs,
    resolve_action,
    should_skip_path,
    summarize_access_ips,
    username_from_request,
    write_audit_log,
)
from services.web_api.config import (
    BOOTSTRAP_ADMIN_PASSWORD,
    BOOTSTRAP_ADMIN_USERNAME,
    BOOTSTRAP_DEV_EMAIL,
    BOOTSTRAP_DEV_PASSWORD,
    BOOTSTRAP_DEV_USERNAME,
    CORS_ORIGINS,
    ESTABELECIMENTOS,
    EXTRACTOR_URL,
    REPORT_URL,
)
from services.web_api.db import Base, SessionLocal, engine, get_db
from services.web_api.deps import (
    get_current_user,
    require_admin,
    require_config_admin,
    require_dev,
    require_user_manager,
)
from services.web_api.http_errors import raise_for_extractor_response
from services.web_api.migrations import run_web_api_migrations
from services.web_api.models import Usuario
from services.web_api.password_reset import request_password_reset, reset_password_with_code
from services.web_api.roles import (
    can_see_filas,
    creatable_roles_by,
    is_global_admin,
    requires_estabelecimento,
)
from services.web_api.schemas import (
    AccessAuditPageOut,
    AccessIpSummaryOut,
    DashboardResumoOut,
    DestinatarioCreate,
    DestinatarioOut,
    DestinatarioUpdate,
    EmitirNotaEspecificaRequest,
    EmitirNotaRequest,
    EnviarRelatorioRequest,
    AtualizarNotaTasyRequest,
    EstabelecimentoConfigOut,
    EstabelecimentoConfigUpdate,
    ForgotPasswordRequest,
    LoginRequest,
    NotaConsultaOut,
    NotaDetalheOut,
    NotaStatusOut,
    NotaStatusPageOut,
    ReemitirNotaRequest,
    ReportSettingsOut,
    ReportSettingsUpdate,
    ResetPasswordRequest,
    Token,
    UsuarioCreate,
    UsuarioOut,
    UsuarioUpdate,
)
from services.common.report_recipients import validate_email as validate_user_email
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
    run_web_api_migrations()
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
        if (
            BOOTSTRAP_DEV_USERNAME
            and BOOTSTRAP_DEV_PASSWORD
            and repository.get_user_by_username(db, BOOTSTRAP_DEV_USERNAME) is None
        ):
            repository.create_user(
                db,
                username=BOOTSTRAP_DEV_USERNAME,
                password=BOOTSTRAP_DEV_PASSWORD,
                role="dev",
                estabelecimento=None,
                email=BOOTSTRAP_DEV_EMAIL,
            )
    finally:
        db.close()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "web_api"}


@app.get("/ops/filas")
def ops_filas(current_user: Usuario = Depends(get_current_user)) -> dict:
    """Profundidade RabbitMQ + saude do processor (circuit breaker / stall)."""
    from services.web_api.ops_status import get_filas_status

    if not can_see_filas(current_user.role):
        raise HTTPException(status_code=403, detail="Acesso restrito ao perfil dev")
    try:
        return get_filas_status()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Nao foi possivel consultar filas/processor: {exc}",
        ) from exc


@app.post("/auth/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return request_password_reset(db, payload.email)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/auth/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return reset_password_with_code(
            db,
            email=payload.email,
            code=payload.code,
            new_password=payload.new_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
    if is_global_admin(current_user.role) or current_user.role == "dev":
        return ESTABELECIMENTOS
    return [current_user.estabelecimento] if current_user.estabelecimento else []


def _resolve_estab_filter(
    current_user: Usuario, estabelecimento: str | None
) -> str | None:
    if is_global_admin(current_user.role) or current_user.role == "dev":
        return estabelecimento
    return current_user.estabelecimento


@app.get("/dashboard/resumo", response_model=DashboardResumoOut)
def dashboard_resumo(
    estabelecimento: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    usar_data_nf: bool = False,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    target = _resolve_estab_filter(current_user, estabelecimento)
    if current_user.role != "adm" and not target:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario sem estabelecimento vinculado",
        )
    return panel_data.dashboard_resumo(
        db,
        estabelecimento=target,
        data_inicio=data_inicio,
        data_fim=data_fim,
        usar_data_nf=usar_data_nf,
    )


@app.get("/dashboard/export")
def dashboard_export(
    estabelecimento: str | None = None,
    status: str | None = None,
    erro_tipo: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    usar_data_nf: bool = False,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = _resolve_estab_filter(current_user, estabelecimento)
    if current_user.role != "adm" and not target:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario sem estabelecimento vinculado",
        )
    rows = panel_data.list_notas_export(
        db,
        estabelecimento=target,
        status=status,
        erro_tipo=erro_tipo,
        data_inicio=data_inicio,
        data_fim=data_fim,
        usar_data_nf=usar_data_nf,
    )
    headers = [
        "id",
        "estabelecimento",
        "nf",
        "nr_sequencia",
        "fornecedor",
        "data_nf",
        "status",
        "tentativas",
        "erro_tipo",
        "erro",
        "pr_id",
        "pr_mensagem",
        "created_at",
        "updated_at",
    ]

    def _cell(value):
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value).replace("\r", " ").replace("\n", " ")

    buffer = io.StringIO()
    buffer.write("\ufeff")  # BOM para Excel
    writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_cell(row.get(col)) for col in headers])

    filename = f"relatorio_notas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/usuarios", response_model=list[UsuarioOut])
def list_usuarios(
    current_user: Usuario = Depends(require_user_manager),
    db: Session = Depends(get_db),
) -> list[Usuario]:
    if is_global_admin(current_user.role):
        return repository.list_users(db)
    return repository.list_users(db, estabelecimento=current_user.estabelecimento)


@app.post("/usuarios", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def create_usuario(
    payload: UsuarioCreate,
    current_user: Usuario = Depends(require_user_manager),
    db: Session = Depends(get_db),
) -> Usuario:
    allowed_roles = creatable_roles_by(current_user.role)
    if payload.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Seu perfil nao pode criar usuarios com papel '{payload.role}'",
        )

    if repository.get_user_by_username(db, payload.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Usuario ja existe"
        )

    email = None
    if payload.email:
        try:
            email = validate_user_email(payload.email)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if repository.get_user_by_email(db, email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="E-mail ja cadastrado"
            )

    if requires_estabelecimento(payload.role):
        if is_global_admin(current_user.role):
            estabelecimento = payload.estabelecimento
        else:
            estabelecimento = current_user.estabelecimento
        if not estabelecimento:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Estabelecimento e obrigatorio para este papel",
            )
        if estabelecimento not in ESTABELECIMENTOS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Estabelecimento invalido",
            )
        if (
            not is_global_admin(current_user.role)
            and estabelecimento != current_user.estabelecimento
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Adm local so cria usuarios do proprio estabelecimento",
            )
    else:
        estabelecimento = None

    return repository.create_user(
        db,
        username=payload.username,
        password=payload.password,
        role=payload.role,
        estabelecimento=estabelecimento,
        email=email,
    )


@app.patch("/usuarios/{user_id}", response_model=UsuarioOut)
def atualizar_usuario(
    user_id: int,
    payload: UsuarioUpdate,
    current_user: Usuario = Depends(require_user_manager),
    db: Session = Depends(get_db),
) -> Usuario:
    target = repository.get_user_by_id(db, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    if (
        not is_global_admin(current_user.role)
        and target.estabelecimento != current_user.estabelecimento
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Adm local so edita usuarios do proprio estabelecimento",
        )

    if "email" not in payload.model_fields_set:
        return target

    email = None
    if payload.email:
        try:
            email = validate_user_email(payload.email)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        existing = repository.get_user_by_email(db, email)
        if existing is not None and existing.id != target.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="E-mail ja cadastrado"
            )

    return repository.update_user_email(db, target, email)


def _resolve_estabelecimento(current_user: Usuario, requested: str | None) -> str:
    if is_global_admin(current_user.role) or current_user.role == "dev":
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
    if is_global_admin(current_user.role) or current_user.role == "dev":
        return
    if nota.get("estabelecimento") != current_user.estabelecimento:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissao para esta nota",
        )


def _parse_data_nf(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        raw = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None
    return None


def _montar_detalhe_com_consulta(nota: dict, consulta: dict) -> dict:
    detalhe = dict(nota)
    detalhe["cd_operacao_nf"] = consulta.get("cd_operacao_nf")
    detalhe["operacoes_liberadas"] = consulta.get("operacoes_liberadas") or []
    detalhe["consulta_mensagem"] = None
    detalhe["preview"] = consulta.get("preview")
    detalhe["depara_resumo"] = None

    if detalhe["preview"]:
        try:
            preview, resumo = enrich_preview_with_depara(
                nota["estabelecimento"], detalhe["preview"]
            )
            detalhe["preview"] = preview
            detalhe["depara_resumo"] = resumo
        except Exception as exc:
            detalhe["depara_resumo"] = None
            detalhe["consulta_mensagem"] = f"Falha ao validar de-para no PR: {exc}"

    if not consulta.get("encontrada"):
        detalhe["consulta_mensagem"] = (
            consulta.get("mensagem") or "Nota nao encontrada no Tasy."
        )
    elif not consulta.get("valido") and not detalhe["preview"]:
        detalhe["consulta_mensagem"] = (
            consulta.get("mensagem") or "Nota sem itens para exibir."
        )
    elif not consulta.get("valido") and detalhe["preview"]:
        detalhe["consulta_mensagem"] = consulta.get("mensagem")

    return detalhe


def _consultar_tasy(estabelecimento: str, nr_sequencia: str) -> dict:
    with httpx.Client(timeout=60.0) as client:
        response = client.get(
            f"{EXTRACTOR_URL}/notas/consultar",
            params={"estabelecimento": estabelecimento, "nr_sequencia": nr_sequencia},
        )
        raise_for_extractor_response(response)
        return response.json()


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
    if is_global_admin(current_user.role) or current_user.role == "dev":
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


@app.post("/notas/{nota_id}/atualizar-tasy", response_model=NotaDetalheOut)
def atualizar_nota_tasy(
    nota_id: int,
    payload: AtualizarNotaTasyRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Puxa a nota atual do Tasy, atualiza o banco auxiliar e opcionalmente reenvia ao PR."""
    nota = panel_data.get_nota_by_id(db, nota_id)
    if nota is None:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")

    _assert_nota_access(current_user, nota)

    nr_sequencia = (nota.get("nr_sequencia") or "").strip()
    if not nr_sequencia:
        raise HTTPException(
            status_code=422,
            detail="Nota sem nr_sequencia para consulta no Tasy.",
        )

    estabelecimento = nota["estabelecimento"]
    try:
        consulta = _consultar_tasy(estabelecimento, nr_sequencia)
    except HTTPException:
        raise
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servico de extracao indisponivel. Verifique o extractor-service.",
        )

    if not consulta.get("encontrada"):
        raise HTTPException(
            status_code=404,
            detail=consulta.get("mensagem") or "Nota nao encontrada no Tasy.",
        )

    preview = consulta.get("preview") or {}
    fornecedor = None
    if isinstance(preview.get("fornecedor"), dict):
        fornecedor = preview["fornecedor"].get("cnpj")
    if not fornecedor:
        fornecedor = consulta.get("fornecedor")

    data_nf = _parse_data_nf(preview.get("dataNF") or consulta.get("data_nf"))
    nf_atualizada = (consulta.get("nf") or preview.get("nf") or nota.get("nf") or "").strip()

    atualizada = panel_data.update_nota_metadata(
        db,
        nota_id,
        nf=nf_atualizada or None,
        fornecedor=fornecedor,
        data_nf=data_nf,
    )
    if atualizada is None:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")

    reenvio = None
    if payload.reenviar:
        if atualizada.get("status") not in REEMITIR_STATUS:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Reenvio permitido apenas para notas com falha "
                    "(retry_pending ou dead_letter). Dados do Tasy ja foram atualizados."
                ),
            )
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{EXTRACTOR_URL}/notas/emitir-especifica",
                    params={
                        "estabelecimento": estabelecimento,
                        "nr_sequencia": nr_sequencia,
                    },
                )
                raise_for_extractor_response(response)
                reenvio = response.json()
        except HTTPException:
            raise
        except httpx.HTTPError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Dados atualizados, mas falha ao reenviar: extractor indisponivel.",
            )

    detalhe = _montar_detalhe_com_consulta(atualizada, consulta)
    if reenvio is not None:
        detalhe["consulta_mensagem"] = (
            (detalhe.get("consulta_mensagem") or "")
            + (" | " if detalhe.get("consulta_mensagem") else "")
            + "Dados atualizados do Tasy e nota reenviada para processamento."
        ).strip(" |")
    else:
        detalhe["consulta_mensagem"] = (
            (detalhe.get("consulta_mensagem") or "")
            + (" | " if detalhe.get("consulta_mensagem") else "")
            + "Dados atualizados do Tasy no painel."
        ).strip(" |")
    return detalhe


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

    nr_sequencia = (nota.get("nr_sequencia") or "").strip()
    if not nr_sequencia:
        detalhe = dict(nota)
        detalhe["cd_operacao_nf"] = None
        detalhe["operacoes_liberadas"] = []
        detalhe["consulta_mensagem"] = "Nota sem nr_sequencia para consulta no Tasy."
        detalhe["preview"] = None
        detalhe["depara_resumo"] = None
        return detalhe

    try:
        consulta = _consultar_tasy(nota["estabelecimento"], nr_sequencia)
    except HTTPException as exc:
        detalhe = dict(nota)
        detalhe["cd_operacao_nf"] = None
        detalhe["operacoes_liberadas"] = []
        detalhe["consulta_mensagem"] = str(exc.detail)
        detalhe["preview"] = None
        detalhe["depara_resumo"] = None
        return detalhe
    except httpx.HTTPError:
        detalhe = dict(nota)
        detalhe["cd_operacao_nf"] = None
        detalhe["operacoes_liberadas"] = []
        detalhe["consulta_mensagem"] = "Servico de extracao indisponivel."
        detalhe["preview"] = None
        detalhe["depara_resumo"] = None
        return detalhe

    return _montar_detalhe_com_consulta(nota, consulta)


@app.get("/admin/logs", response_model=NotaStatusPageOut)
def listar_logs(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
    estabelecimento: str | None = None,
    status: str | None = None,
    erro_tipo: str | None = None,
    somente_erro: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    target = _resolve_estab_filter(current_user, estabelecimento)
    return panel_data.list_logs(
        db,
        estabelecimento=target,
        status=status,
        erro_tipo=erro_tipo,
        somente_erro=somente_erro,
        page=page,
        page_size=page_size,
    )


@app.get("/admin/acesso/resumo", response_model=AccessIpSummaryOut)
def resumir_acesso_ips(
    _: Usuario = Depends(require_dev),
    db: Session = Depends(get_db),
    username: str | None = None,
    estabelecimento: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    top: int = 50,
) -> dict:
    return summarize_access_ips(
        db,
        username=username,
        estabelecimento=estabelecimento,
        data_inicio=data_inicio,
        data_fim=data_fim,
        top=top,
    )


@app.get("/admin/acesso", response_model=AccessAuditPageOut)
def listar_acesso(
    _: Usuario = Depends(require_dev),
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
    if is_global_admin(current_user.role) or current_user.role == "dev":
        return estabelecimento
    return current_user.estabelecimento


@app.get("/destinatarios", response_model=list[DestinatarioOut])
def listar_destinatarios(
    estabelecimento: str | None = None,
    current_user: Usuario = Depends(get_current_user),
) -> list[dict]:
    target = _resolve_destinatario_estabelecimento(current_user, estabelecimento)
    if (
        not is_global_admin(current_user.role)
        and current_user.role != "dev"
        and not target
    ):
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
    if is_global_admin(current_user.role) or current_user.role == "dev":
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
        return create_recipient(
            estabelecimento=target,
            email=payload.email,
            ativo=payload.ativo,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/destinatarios/{recipient_id}", response_model=DestinatarioOut)
def editar_destinatario(
    recipient_id: int,
    payload: DestinatarioUpdate,
    current_user: Usuario = Depends(get_current_user),
) -> dict:
    allowed = (
        None
        if is_global_admin(current_user.role) or current_user.role == "dev"
        else current_user.estabelecimento
    )
    try:
        return update_recipient(
            recipient_id=recipient_id,
            email=payload.email,
            ativo=payload.ativo,
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
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Exclusao desabilitada. Use PATCH com ativo=false para inativar o destinatario.",
    )


@app.get("/admin/estabelecimentos/config", response_model=list[EstabelecimentoConfigOut])
def listar_config_estabelecimentos(
    _: Usuario = Depends(require_config_admin),
) -> list[dict]:
    return list_estab_configs()


@app.patch(
    "/admin/estabelecimentos/{estabelecimento}/config",
    response_model=EstabelecimentoConfigOut,
)
def atualizar_config_estabelecimento(
    estabelecimento: str,
    payload: EstabelecimentoConfigUpdate,
    _: Usuario = Depends(require_config_admin),
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
    _: Usuario = Depends(require_config_admin),
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


@app.get("/admin/relatorios/config", response_model=ReportSettingsOut)
def obter_config_relatorio(_: Usuario = Depends(require_config_admin)) -> dict:
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(f"{REPORT_URL}/relatorios/config")
            if response.is_error:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except HTTPException:
        raise
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servico de relatorio indisponivel. Verifique o report-service.",
        )


@app.patch("/admin/relatorios/config", response_model=ReportSettingsOut)
def atualizar_config_relatorio(
    payload: ReportSettingsUpdate,
    _: Usuario = Depends(require_config_admin),
) -> dict:
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.patch(
                f"{REPORT_URL}/relatorios/config",
                json={"report_interval_minutes": payload.report_interval_minutes},
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
    _: Usuario = Depends(require_config_admin),
) -> dict:
    cfg = get_estab_config(estabelecimento)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Estabelecimento nao encontrado")
    return cfg
