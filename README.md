# Projet Parfums (nom provisoire)

Boutique en ligne de parfums pour la Côte d'Ivoire : Next.js (frontend) + FastAPI (API) + PostgreSQL.

- Suivi du projet et décisions : [`SUIVI.md`](SUIVI.md)
- Conception : [`docs/`](docs/)

## Prérequis

| Outil | Version | Installation (macOS) |
|---|---|---|
| Node.js | 22 LTS | déjà requis |
| pnpm | 11 (activé par Corepack via `packageManager`) | `corepack enable` |
| uv (gère Python 3.13) | dernière | `python3 -m pip install --user uv` puis `export PATH="$HOME/Library/Python/3.9/bin:$PATH"` (ou `brew install uv` sur un macOS récent) |
| PostgreSQL | 17 | [Postgres.app](https://postgresapp.com) (glisser dans Applications, ouvrir, « Initialize »), ou `docker compose up -d` |

Sur macOS 13, Homebrew n'a plus de paquets précompilés : `brew install` compile depuis les sources (très long). Préférer les méthodes ci-dessus.

## Premier démarrage

```bash
# 1. Base de données (Postgres.app démarré)
export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"
createdb parfums
createdb parfums_test

# 2. Backend — http://localhost:8000/api/v1/docs
cd backend
cp .env.example .env         # puis renseigner SECRET_KEY (commande de génération dans le fichier)
uv sync                       # installe Python 3.13 et les dépendances
uv run alembic upgrade head   # applique les migrations
uv run fastapi dev app/main.py

# 3. Frontend — http://localhost:3000 (dans un autre terminal)
cd frontend
cp .env.example .env.local
pnpm install
pnpm dev
```

La page d'accueil affiche « API : connectée » quand le frontend joint le backend, qui joint la base.

## Commandes utiles

| Action | Backend (`backend/`) | Frontend (`frontend/`) |
|---|---|---|
| Lancer | `uv run fastapi dev app/main.py` | `pnpm dev` |
| Tests | `uv run pytest` | `pnpm test` |
| Tests de parcours (navigateur) | — | `pnpm test:e2e` (backend lancé ; première fois : `pnpm exec playwright install chromium` — non disponible sur macOS 13, ces tests tournent alors dans la CI) |
| Lint | `uv run ruff check . && uv run ruff format --check .` | `pnpm lint` |
| Typage | `uv run mypy` | `pnpm typecheck` |
| Nouvelle migration | `uv run alembic revision --autogenerate -m "description"` | — |
| Appliquer les migrations | `uv run alembic upgrade head` | — |
| Créer le premier Propriétaire | `uv run python -m app.scripts.create_owner <e-mail>` | — |

Les tests du backend utilisent la base `parfums_test` (variable `TEST_DATABASE_URL`), jamais la base de développement.

**Nouvelle migration — à relire avant de l'appliquer.** L'autogénération d'Alembic :
- écrit chaque contrainte d'énumération en triple : garder seulement le `sa.CheckConstraint(..., name=op.f("ck_…"))` et passer `create_constraint=False` dans le `sa.Enum(...)` rendu (voir la migration `0002`) ;
- ne détecte pas les séquences (`order_number_seq`) : les écrire à la main.

`uv run alembic check` (aussi exécuté en CI) vérifie ensuite que modèles et migrations correspondent.

## Intégration continue

GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) exécute à chaque envoi sur `main` : lint, typage, migrations et tests du backend sur un vrai PostgreSQL 17 ; lint, typage, tests et build du frontend ; parcours navigateur de bout en bout (Chromium mobile et ordinateur).
