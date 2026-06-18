import httpx
from datetime import date
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from services.web_api import panel_data, repository
from services.web_api.config import (
    BOOTSTRAP_ADMIN_PASSWORD,
    BOOTSTRAP_ADMIN_USERNAME,
    CORS_ORIGINS,
    ESTABELECIMENTOS,
    EXTRACTOR_URL,
)
from services.web_api.db import Base, SessionLocal, engine, get_db
from services.web_api.deps import get_current_user, require_admin
from services.web_api.models import Usuario
from services.web_api.schemas import (
    EmitirNotaEspecificaRequest,
    EmitirNotaRequest,
    LoginRequest,
    NotaConsultaOut,
    NotaStatusOut,
    ReemitirNotaRequest,
    Token,
    UsuarioCreate,
    UsuarioOut,
)
from services.web_api.security import create_access_token, verify_password

app = FastAPI(title="Web API - Painel NF")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
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
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = repository.get_user_by_username(db, payload.username)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario ou senha invalidos",
        )
    token = create_access_token(
        subject=user.username, role=user.role, estabelecimento=user.estabelecimento
    )
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
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{EXTRACTOR_URL}/run", params={"estabelecimento": estabelecimento}
            )
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao acionar extracao: {exc}",
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
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{EXTRACTOR_URL}/notas/consultar",
                params={"estabelecimento": target, "nr_sequencia": nr_sequencia},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao consultar nota: {exc}",
        )


@app.post("/notas/emitir-especifica")
def emitir_nota_especifica(
    payload: EmitirNotaEspecificaRequest,
    current_user: Usuario = Depends(get_current_user),
) -> dict:
    target = _resolve_estabelecimento(current_user, payload.estabelecimento)
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{EXTRACTOR_URL}/notas/emitir-especifica",
                params={
                    "estabelecimento": target,
                    "nr_sequencia": payload.nr_sequencia.strip(),
                },
            )
            if response.status_code == 422:
                detail = response.json().get("detail", "Nota nao elegivel")
                raise HTTPException(status_code=422, detail=detail)
            response.raise_for_status()
            result = response.json()
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao emitir nota especifica: {exc}",
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
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{EXTRACTOR_URL}/notas/emitir-especifica",
                params={"estabelecimento": estabelecimento, "nr_sequencia": nr_sequencia},
            )
            if response.status_code == 422:
                detail = response.json().get("detail", "Nota nao elegivel")
                raise HTTPException(status_code=422, detail=detail)
            response.raise_for_status()
            result = response.json()
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao reemitir nota: {exc}",
        )

    return {
        "id": payload.id,
        "estabelecimento": estabelecimento,
        "nr_sequencia": nr_sequencia,
        "nf": nota.get("nf"),
        "resultado": result,
    }


@app.get("/notas", response_model=list[NotaStatusOut])
def listar_notas(
    estabelecimento: str | None = None,
    nf: str | None = None,
    nr_sequencia: str | None = None,
    fornecedor: str | None = None,
    status: str | None = None,
    data_nf_inicio: date | None = None,
    data_nf_fim: date | None = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
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
        data_nf_inicio=data_nf_inicio,
        data_nf_fim=data_nf_fim,
    )
