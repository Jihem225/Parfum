from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from app.core import rate_limit, security
from app.core.audit import audit
from app.core.config import settings
from app.core.email import send_email
from app.core.errors import AppError
from app.modules.auth import service
from app.modules.auth.deps import (
    DB,
    SESSION_COOKIE,
    CurrentUser,
    client_ip,
    require_roles,
)
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    ChangePasswordIn,
    ForgotPasswordIn,
    LoginIn,
    MessageOut,
    RegisterIn,
    ResetPasswordIn,
    TotpEnableIn,
    TotpEnableOut,
    TotpSetupOut,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])

MINUTES_15 = 15 * 60
HOUR = 3600
MAX_LOGIN_FAILURES = 5


def _set_session_cookie(response: Response, raw: str, ttl: timedelta) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        raw,
        max_age=int(ttl.total_seconds()),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


def _open_session(db: DB, request: Request, response: Response, user: User) -> None:
    raw, ttl = service.create_session(
        db, user, user_agent=request.headers.get("user-agent"), ip=client_ip(request)
    )
    db.commit()
    _set_session_cookie(response, raw, ttl)


@router.post("/register", status_code=201)
def register(data: RegisterIn, request: Request, response: Response, db: DB) -> UserOut:
    rate_limit.limit(f"register:ip:{client_ip(request)}", 10, HOUR)
    user = service.register(
        db, email=data.email, password=data.password, full_name=data.full_name, phone=data.phone
    )
    _open_session(db, request, response, user)
    return UserOut.of(user)


@router.post("/login")
def login(data: LoginIn, request: Request, response: Response, db: DB) -> UserOut:
    rate_limit.limit(f"login:ip:{client_ip(request)}", 30, MINUTES_15)
    failures_key = f"login:fail:{data.email}"
    if rate_limit.hits(failures_key, MINUTES_15) >= MAX_LOGIN_FAILURES:
        raise rate_limit.too_many()
    try:
        user = service.authenticate(
            db, email=data.email, password=data.password, totp_code=data.totp_code
        )
    except AppError as exc:
        if exc.code in {"INVALID_CREDENTIALS", "TOTP_INVALID"}:
            rate_limit.record_hit(failures_key, MINUTES_15)
        raise
    _open_session(db, request, response, user)  # valide aussi un code de secours consommé
    return UserOut.of(user)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: DB) -> None:
    raw = request.cookies.get(SESSION_COOKIE)
    if raw:
        service.end_session(db, raw)
        db.commit()
    response.delete_cookie(SESSION_COOKIE)


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut.of(user)


@router.post("/forgot-password", status_code=202)
def forgot_password(
    data: ForgotPasswordIn, request: Request, db: DB, background: BackgroundTasks
) -> MessageOut:
    rate_limit.limit(f"forgot:ip:{client_ip(request)}", 10, HOUR)
    rate_limit.limit(f"forgot:email:{data.email}", 3, HOUR)
    started = service.start_password_reset(db, data.email)
    if started:
        user, raw = started
        db.commit()
        link = f"{settings.frontend_origin}/compte/reinitialiser?token={raw}"
        background.add_task(
            send_email,
            user.email,
            "Réinitialisation de votre mot de passe",
            f"Bonjour {user.full_name},\n\nPour choisir un nouveau mot de passe, ouvrez ce lien "
            f"(valable 1 heure) :\n{link}\n\nSi vous n'êtes pas à l'origine de cette demande, "
            "ignorez ce message.",
        )
    # Même réponse que le compte existe ou non : pas d'énumération des e-mails.
    return MessageOut(message="Si un compte existe pour cet e-mail, un lien vient d'être envoyé.")


@router.post("/reset-password")
def reset_password(data: ResetPasswordIn, request: Request, db: DB) -> MessageOut:
    rate_limit.limit(f"reset:ip:{client_ip(request)}", 20, HOUR)
    service.reset_password(db, token=data.token, password=data.password)
    db.commit()
    return MessageOut(message="Mot de passe modifié. Vous pouvez vous connecter.")


@router.post("/change-password")
def change_password(
    data: ChangePasswordIn, request: Request, user: CurrentUser, db: DB
) -> MessageOut:
    raw = request.cookies.get(SESSION_COOKIE)
    service.change_password(
        db,
        user,
        current=data.current_password,
        new=data.new_password,
        keep_session_hash=security.sha256(raw) if raw else None,
    )
    db.commit()
    return MessageOut(message="Mot de passe modifié. Vos autres appareils ont été déconnectés.")


StaffNeedingTotp = Annotated[
    User, Depends(require_roles(*service.TOTP_ROLES, allow_without_totp=True))
]


@router.post("/totp/setup")
def totp_setup(user: StaffNeedingTotp) -> TotpSetupOut:
    if user.totp_secret:
        raise AppError(409, "TOTP_ALREADY_ENABLED", "La double authentification est déjà active.")
    secret = security.new_totp_secret()
    return TotpSetupOut(secret=secret, otpauth_uri=security.totp_uri(secret, user.email))


@router.post("/totp/enable")
def totp_enable(
    data: TotpEnableIn, request: Request, user: StaffNeedingTotp, db: DB
) -> TotpEnableOut:
    codes = service.enable_totp(user, secret=data.secret, code=data.code)
    audit(
        db,
        actor_id=user.id,
        action="auth.totp_enable",
        entity_type="user",
        entity_id=user.id,
        ip=client_ip(request),
    )
    db.commit()
    return TotpEnableOut(recovery_codes=codes)
