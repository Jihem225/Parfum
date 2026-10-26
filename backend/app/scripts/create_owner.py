"""Crée le premier compte Propriétaire : uv run python -m app.scripts.create_owner <e-mail>"""

import argparse
import getpass
import sys

from pydantic import TypeAdapter, ValidationError

from app.core import security
from app.core.audit import audit
from app.core.db import SessionLocal
from app.core.validators import Password, PersonName, Phone
from app.modules.auth.models import User, UserRole
from app.modules.auth.schemas import Email
from app.modules.auth.service import find_by_email


def main() -> int:
    parser = argparse.ArgumentParser(description="Crée un compte Propriétaire.")
    parser.add_argument("email")
    args = parser.parse_args()
    try:
        email = TypeAdapter(Email).validate_python(args.email)
        full_name = TypeAdapter(PersonName).validate_python(input("Nom complet : "))
        phone = TypeAdapter(Phone).validate_python(input("Téléphone : "))
        password = getpass.getpass("Mot de passe (10 caractères minimum) : ")
        TypeAdapter(Password).validate_python(password)
    except ValidationError as exc:
        print(f"Saisie invalide : {exc.errors()[0]['msg']}", file=sys.stderr)
        return 1
    if getpass.getpass("Confirmez le mot de passe : ") != password:
        print("Les mots de passe ne correspondent pas.", file=sys.stderr)
        return 1
    with SessionLocal() as db:
        if find_by_email(db, email):
            print("Un compte existe déjà avec cet e-mail.", file=sys.stderr)
            return 1
        user = User(
            email=email,
            password_hash=security.hash_password(password),
            full_name=full_name,
            phone=phone,
            role=UserRole.OWNER,
        )
        db.add(user)
        db.flush()
        audit(
            db, actor_id=None, action="staff.bootstrap_owner", entity_type="user", entity_id=user.id
        )
        db.commit()
    print(
        "Propriétaire créé. À la première connexion, activez la double authentification "
        "(obligatoire pour accéder à l'administration)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
