# Suivi du projet — « Projet Parfums » (nom provisoire)

Document de reprise : à lire en premier après toute interruption.

## Étape actuelle

**Étape 6.4 — Backend : produits, contenances et images** : en cours.

- Étape 6.3 — Collections et familles olfactives : **validée le 2026-10-26**.

- Étape 6.2 — Authentification et permissions : **validée le 2026-10-26**.

- Étape 6.1 — Base de données et migrations : **validée le 2026-10-26**. Le porteur autorise le commit + push de chaque sous-étape validée.

- Étape 5 — Initialisation : **terminée le 2026-10-26** ; passage à l'étape 6 autorisé d'avance par le porteur (« dès que c'est OK tu passes à l'étape suivante »). Premier commit autorisé et effectué.

- Étape 4 — Conception UI/UX : **validée le 2026-10-26** ([`docs/04-maquettes.md`](docs/04-maquettes.md), canevas https://claude.ai/artifact/1bF31hbjmR5b2TqJgMDrXr).

- Étape 1 — Cadrage : **validée le 2026-10-26** (hypothèses par défaut comprises).
- Étape 2 — Conception fonctionnelle : **validée le 2026-10-26** ([`docs/02-conception-fonctionnelle.md`](docs/02-conception-fonctionnelle.md)). Points §10 : propositions retenues pour 1 (5 unités / 300 000 FCFA), 2 (3 appels / 48 h) et 5 (pas de rattachement des commandes invité) ; points 3, 4, 6, 7, 8 = contenu ou paramètres à fournir plus tard.
- Étape 3 — Conception technique : **validée le 2026-10-26** ([`docs/03-conception-technique.md`](docs/03-conception-technique.md)) : hébergement Render + Cloudflare + R2, TOTP pour Propriétaire et Gestionnaire, PostgreSQL Homebrew + Python 3.13 via uv.

## Décisions validées par le porteur du projet

| Date | Décision |
|---|---|
| 2026-10-26 | Dépôt dédié : https://github.com/Jihem225/Parfum (séparé de LaCarte, qui est une app de restaurant). |
| 2026-10-26 | Stack : celle du prompt maître — Next.js + TypeScript strict + Tailwind + shadcn/ui (frontend), FastAPI + Pydantic + SQLAlchemy + Alembic + PostgreSQL (backend). |
| 2026-10-26 | Modèle commercial : vente de **sa propre marque** de parfums. |
| 2026-10-26 | Paiement au lancement : **paiement à la livraison uniquement**. |

## Conséquences retenues (validées avec l'étape 1)

- Marque unique : pas de table `brands` ; la navigation « par marques » devient une navigation par **collections**.
- Pas de prestataire de paiement au MVP. Le modèle `payments` garde un champ « moyen » et une interface prestataire pour ajouter le mobile money plus tard sans refonte.
- Paiement à la livraison : le livreur encaisse, puis l'admin enregistre la remise d'espèces ; rapprochement des encaissements par livreur.
- Confirmation téléphonique de la commande avant expédition (limite les refus).
- Stock réservé à la commande, libéré en cas d'annulation ou de refus à la livraison.

## Hypothèses par défaut (validées avec l'étape 1, révisables)

| Question | Hypothèse |
|---|---|
| 3b. Boutique physique partageant le stock ? | Non (vente en ligne uniquement). |
| 4. Volume | < 100 références au lancement, < 50 commandes/jour. |
| 6. Livraison | Abidjan uniquement, tarif par commune, livreurs internes, pas de retrait. |
| 7. Compte client | Commande sans compte autorisée ; téléphone obligatoire ; connexion e-mail + mot de passe. |
| 8. Back-office | 3 rôles fixes : Propriétaire, Gestionnaire, Livreur. |
| 9. Identité | Nom de code « Projet Parfums » ; nom, logo et photos fournis par le porteur. |
| 10. Budget / date | Non fixés ; hébergement à chiffrer à l'étape 3. |

## Périmètre MVP proposé

Boutique (accueil, catalogue par collections, recherche, filtres genre / famille olfactive / prix / contenance / disponibilité, tri, fiche produit avec variantes 30/50/100 ml, panier, commande avec ou sans compte, confirmation, suivi), paiement à la livraison, livraison par zones, espace client de base (compte, adresses, commandes), back-office (tableau de bord simple, catalogue, stock avec mouvements et alertes, commandes avec statuts et livreur, encaissements, journal d'audit), pages légales, FAQ, contact.

Reporté après le MVP : mobile money (Orange, MTN, Wave), carte bancaire, avis, favoris, codes promo, bannières administrables, newsletter, paniers abandonnés, permissions granulaires, multi-pays.

## Fichiers du projet

- `SUIVI.md` — ce document (commité).
- `docs/02-conception-fonctionnelle.md` — conception fonctionnelle du MVP (commité).
- `docs/03-conception-technique.md` — architecture, versions, modèle de données, API, sécurité, hébergement (commité).
- `docs/04-maquettes.md` + `docs/maquettes/` — maquettes des 10 écrans et charte provisoire (commité).
- `README.md`, `.gitignore`, `docker-compose.yml`, `.github/workflows/ci.yml` — démarrage, CI (commité).
- `backend/` — FastAPI : config, connexion base, `/api/v1/health`, Alembic (migration 0001 : extension `unaccent`), tests (commité).
- `backend/app/modules/*/models.py`, `backend/app/core/models.py`, `backend/app/models.py` — modèle de données (6.1, commité)
- `backend/alembic/versions/…0002_modele_de_donnees_mvp.py` — migration du modèle (6.1, commité)
- `backend/tests/test_schema.py` — tests des contraintes (6.1, commité)
- `backend/app/core/{errors,security,rate_limit,csrf,audit,email,validators}.py` — socle commun (6.2, commité)
- `backend/app/modules/auth/{schemas,service,deps,router}.py`, `backend/app/modules/staff/router.py`, `backend/app/scripts/create_owner.py` — authentification, collaborateurs (6.2, commité)
- `backend/tests/test_auth.py`, `backend/tests/test_staff.py` (6.2, commité)
- `backend/app/core/slug.py`, `backend/app/modules/catalog/{schemas,taxonomy,router}.py`, `backend/tests/test_taxonomy.py` — collections et familles (6.3, commité)
- `frontend/` — Next.js 16.4.3 : charte, relais `/api/v1`, page provisoire, Vitest, Playwright (commité).

## Tests exécutés

| Date | Commande | Résultat |
|---|---|---|
| 2026-10-26 | frontend `pnpm lint` / `pnpm typecheck` | OK / OK |
| 2026-10-26 | frontend `pnpm test` (Vitest) | 2/2 réussis |
| 2026-10-26 | frontend `pnpm build` (Next.js 16.4.3) | OK |
| 2026-10-26 | frontend `pnpm audit` | 0 vulnérabilité (après passage 16.4.0 → 16.4.3) |
| 2026-10-26 | backend `ruff check`, `ruff format --check`, `mypy` (strict) | OK |
| 2026-10-26 | backend `pip-audit` | 0 vulnérabilité |
| 2026-10-26 | backend `alembic upgrade head` (dev + test), `downgrade base` puis `upgrade head` | OK ; `unaccent('Ambré Néroli')` → `Ambre Neroli` |
| 2026-10-26 | backend `pytest` (PostgreSQL 17.11, Postgres.app) | 2/2 réussis |
| 2026-10-26 | démarrage réel : `fastapi run` (:8000) + `next start` (:3000) | `/api/v1/health` 200 en direct et via le relais Next.js ; accueil affiche « API : connectée » ; docs OpenAPI 200 |
| 2026-10-26 | 6.1 : `alembic upgrade head` (0001 → 0002), `alembic check`, aller-retour `downgrade base` / `upgrade head` | OK ; 22 tables, 33 contraintes CHECK, 26 clés étrangères, séquence à 10001 |
| 2026-10-26 | 6.1 : `pytest` (santé + 13 tests de contraintes) | 15/15 réussis |
| 2026-10-26 | CI GitHub (après push 6.1 + correctif) | backend, frontend, e2e : verts ; E2E Playwright 2/2 (mobile + ordinateur) |
| 2026-10-26 | 6.2 : `pytest` | 48/48 réussis (santé, schéma, authentification, collaborateurs) |
| 2026-10-26 | 6.2 : parcours HTTP réel via le relais Next.js | CSRF refusé sans jeton (403), inscription 201 + cookie HttpOnly, /me 200, déconnexion 204, /me 401, admin anonyme 401, mauvais mot de passe 401 |
| 2026-10-26 | 6.2 : script `create_owner` (base de test) | Propriétaire créé, Argon2id, audit tracé |
| 2026-10-26 | CI GitHub (commit 6.2) | backend, frontend, e2e : verts |
| 2026-10-26 | 6.3 : `pytest` | 56/56 réussis |
| 2026-10-26 | 6.3 : appels réels via le relais | listes publiques 200, collection inconnue 404, écriture anonyme 401 |
| — | E2E Playwright | non exécuté en local (Chromium indisponible sur macOS 13) → job `e2e` de la CI, pas encore exécuté (dépôt non poussé) |

## Problèmes connus / risques

- Refus et absences au paiement à la livraison ; argent liquide détenu par les livreurs.
- Notoriété d'une marque nouvelle : la qualité des photos et du contenu est déterminante.
- Réglementation des cosmétiques (étiquetage, composition, allergènes) : à vérifier avec un professionnel.
- Données personnelles (loi ivoirienne n° 2013-450, ARTCI) : à confirmer avec un juriste.
- Deux services à héberger (Next.js + FastAPI) : coût et complexité de déploiement plus élevés qu'un monolithe.
- macOS 13 du poste de développement : plus de paquets Homebrew précompilés, pas de Chromium Playwright. Contournements : uv via pip, Postgres.app, E2E en CI.
- ESLint 9 n'est plus maintenu ; passage à ESLint 10 quand les plugins de Next.js le supporteront.
- `uv` n'est pas dans le PATH par défaut : `export PATH="$HOME/Library/Python/3.9/bin:$PATH"`.

## Prochaine action

Obtenir la validation de l'étape 6.3 (puis commit + push), puis étape 6.4 : produits, contenances et images (création, publication RG-03, archivage RG-04, catalogue public avec recherche, filtres, tri, fiche produit et produits similaires).

Environnement local : macOS 13, Node 22, pnpm 11 (Corepack), Python 3.13 via uv (`~/Library/Python/3.9/bin/uv`), PostgreSQL 17.11 via Postgres.app ; pas de Docker.
