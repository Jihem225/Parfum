from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, StringConstraints

from app.core.validators import Password, PersonName, Phone, normalize_email
from app.modules.auth.models import User, UserRole

Email = Annotated[EmailStr, AfterValidator(normalize_email)]
ShortText = Annotated[str, StringConstraints(max_length=200)]


class RegisterIn(BaseModel):
    email: Email
    password: Password
    full_name: PersonName
    phone: Phone


class LoginIn(BaseModel):
    email: Email
    password: Annotated[str, StringConstraints(max_length=128)]
    totp_code: Annotated[str, StringConstraints(max_length=20)] | None = None


class ForgotPasswordIn(BaseModel):
    email: Email


class ResetPasswordIn(BaseModel):
    token: ShortText
    password: Password


class ChangePasswordIn(BaseModel):
    current_password: Annotated[str, StringConstraints(max_length=128)]
    new_password: Password


class TotpSetupOut(BaseModel):
    secret: str
    otpauth_uri: str


class TotpEnableIn(BaseModel):
    secret: Annotated[str, StringConstraints(max_length=64)]
    code: Annotated[str, StringConstraints(max_length=10)]


class TotpEnableOut(BaseModel):
    recovery_codes: list[str]


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    phone: str
    role: UserRole
    is_active: bool
    totp_enabled: bool
    last_login_at: datetime | None

    @classmethod
    def of(cls, user: User) -> "UserOut":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            role=user.role,
            is_active=user.is_active,
            totp_enabled=user.totp_secret is not None,
            last_login_at=user.last_login_at,
        )


class MessageOut(BaseModel):
    message: str
