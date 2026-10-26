# Suivi du projet — « Projet Parfums » (nom provisoire)

Document de reprise : à lire en premier après toute interruption.

## Étape actuelle

**Étape 13 — Codes promo** (hors prompt, 2026-10-26 ; mise en ligne, prestataire et Pillow reportés par le porteur : « on le fera après ») : **validée le 2026-10-26** (« valide »). Décisions du porteur : % (plafond facultatif) ou montant fixe ; sur les articles hors livraison ; dates, nombre total et 1 fois par téléphone ; annulation = code rendu. Règles RG-80 à RG-86 (docs/02 §12).

**Étape 12 — File d'envoi des e-mails** (hors prompt, choisie le 2026-10-26 en attendant les comptes de mise en ligne) : **validée le 2026-10-26** (« valide et pousse »). E-mails écrits dans `email_outbox` avec l'action, envoyés par une tâche de fond toutes les 5 s, nouveaux essais (1, 5, 15, 60, 180 min) puis « en échec », page **E-mails** du back-office avec renvoi, alerte au tableau de bord.

**Étape 11 — Mobile money** (hors prompt, demandée le 2026-10-26 ; mise en ligne repoussée à la fin par le porteur) : 11.1 backend **validée le 2026-10-26** (« continue ce projet ») ; 11.2 frontend **validée le 2026-10-26** (« valide ») ; 11.3 documentation **validée le 2026-10-26** (« valide »). **Étape 11 terminée** ; reste la mise en ligne.

Décisions du porteur (2026-10-26) : prestataire **pas encore choisi** → interface neutre + prestataire de simulation (développement / CI, refusé en production) ; **pas de plafond** de 300 000 FCFA pour le mobile money ; commande payée = **Confirmée sans appel** ; non payée en **30 minutes** = annulée, stock libéré.

**Les 10 étapes du prompt maître sont validées (2026-10-26).** Étape 10 — Livraison et maintenance : **validée le 2026-10-26** (« valide »), bilan : [`docs/10-bilan.md`](docs/10-bilan.md).

**En attente du porteur pour la mise en ligne** : nom de domaine, comptes Render / Cloudflare / Resend, décision sur la préproduction.

- Étape 9 — Déploiement (préparation) : **validée le 2026-10-26** (« valide »). Rien n'est encore en ligne.

- Étape 8 — Intégration et tests complets : **validée le 2026-10-26** (« passe à l'étape suivante »).

- Étape 7 — Frontend : **validée le 2026-10-26** (« lance l'étape suivante »). Sous-étapes 7.1 à 7.5 enchaînées sans validation intermédiaire à la demande du porteur.

- Étape 6.10 — Pilotage et compléments du back-office : **validée le 2026-10-26** (6.10 promos et 6.11 avis/favoris du prompt maître : hors MVP). **Étape 6 (backend) terminée.**

- Étape 6.9 — Livraison, retours et compte client : **validée le 2026-10-26**, avec la proposition 6.10 « pilotage et compléments ».

- Étape 6.8 — Encaissements : **validée le 2026-10-26**.

- Étape 6.7 — Commandes (avec communes desservies) : **validée le 2026-10-26** ; ordre 6.8 puis 6.9 conservé.

- Étape 6.6 — Panier : **validée le 2026-10-26**, avec la proposition d'avancer les communes desservies (frais, délais) dans 6.7.

- Étape 6.5 — Stock : **validée le 2026-10-26**.

- Étape 6.4 — Produits, contenances et images : **validée le 2026-10-26**.

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

Reporté après le MVP : mobile money (Orange, MTN, Wave ; fait à l'étape 11), carte bancaire, avis, favoris, codes promo (fait à l'étape 13), bannières administrables, newsletter, paniers abandonnés, permissions granulaires, multi-pays.

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
- `backend/app/core/{storage,images}.py`, `backend/app/modules/catalog/{products,queries,products_router}.py`, `backend/tests/test_products.py` — produits, contenances, images, catalogue public (6.4, commité)
- `backend/app/modules/inventory/{service,schemas,router}.py`, `backend/tests/test_stock.py` — stock : entrées, ajustements, historique, alertes de seuil, fonctions atomiques réserver / libérer / sortir / retour / perte (6.5, commité)
- `backend/app/modules/cart/{service,schemas,router}.py`, fusion à la connexion dans `auth/router.py`, `backend/tests/test_cart.py` — panier visiteur (cookie) et client, fusion, contrôles 5 unités / disponible / publié, plafond 300 000 FCFA (6.6, commité)
- `backend/app/modules/delivery/{schemas,router}.py` (communes), `backend/app/modules/orders/{schemas,service,notify,router}.py`, `backend/app/core/errors.py` (messages de validation en français), `backend/tests/test_orders.py` — commandes (6.7, commité)
- `backend/app/modules/payments/{schemas,router}.py`, `backend/app/modules/delivery/courier.py`, « Livrée » et `/checkout/preview` dans `orders/`, `backend/tests/test_cash.py` — livraison encaissée, espèces par livreur, remises de caisse (6.8, commité)
- `backend/app/modules/customers/{schemas,router}.py` (profil, adresses), échec / nouvelle tentative / retour dans `orders/service.py`, `orders/router.py` et `delivery/courier.py`, `backend/tests/test_delivery.py` (6.9, commité)
- `backend/app/modules/{dashboard,audit}/router.py`, `contact/router.py`, `settings/router.py`, `customers/admin.py`, `core/validators.py` (numéros fixes acceptés), `backend/tests/test_backoffice.py` (6.10, commité)
- `frontend/` — Next.js 16.4.3, étape 7 (commité) :
  - 7.1 socle : `src/lib/{api,server-api,types,format,schemas,hooks,navigation}.ts`, `src/components/{ui,providers,product-image,order-view}.tsx`, relais `/media`, en-têtes de sécurité, pages d'erreur ;
  - 7.2 boutique `src/app/(boutique)/` : accueil, `parfums`, `parfums/[slug]`, `collections`, `panier`, `commande` (+ `confirmee`), `suivi`, `contact`, `infos/[page]`, `sitemap.ts`, `robots.ts` ;
  - 7.3 compte `src/app/(boutique)/compte/` : connexion, inscription, mot de passe oublié / réinitialisation, profil, adresses, commandes (+ annulation) ;
  - 7.4 back-office `src/app/admin/` : connexion (2FA), activation 2FA, tableau de bord, commandes (+ impression bon / bordereau), produits, collections et familles, stock et mouvements, encaissements, clients, messages, paramètres, collaborateurs, journal ;
  - 7.5 livreur `src/app/livreur/` : connexion, mes livraisons, livrée et encaissée, échec ;
  - tests : `src/lib/*.test.ts` (Vitest), `e2e/{boutique,compte,backoffice}.spec.ts` + `e2e/order.ts` (Playwright, CI ; étape 8 : recherche, rupture, annulation client, accès back-office).
- Étape 13 : `backend/app/modules/promotions/{models,service,router}.py`, migration `0005` (table `promo_codes`, `orders.discount` / `promo_code_id` / `promo_code`, contrainte `total = subtotal - discount + delivery_fee`), `orders/{models,schemas,service,router,notify}.py`, `dashboard/router.py` (CA net, `discounts`), `core/config.py` (`ORDER_RATE_LIMIT`, 10 par défaut ; 100 dans le job e2e de la CI car les 13 parcours commandent depuis la même IP), `scripts/seed_demo.py` (code fictif `BIENVENUE10`), `backend/tests/test_promotions.py` ; frontend : récapitulatif (`commande/page.tsx`), `order-view.tsx`, fiche commande, `admin/(app)/codes-promo/page.tsx`, tableau de bord, `e2e/promo.spec.ts` ; docs 02 §12, 03, 10-guide, 10-bilan.
- Étape 12 : `backend/app/core/{email,models}.py` (file d'envoi, `EmailMessage`), migration `0004`, `backend/app/modules/emails/router.py`, envois mis en file dans `orders/{router,jobs}.py`, `delivery/courier.py`, `auth/router.py`, `contact/router.py`, `inventory/service.py` (alerte avant validation), `dashboard/router.py` (`failed_emails`), `main.py` (tâche d'envoi) ; `backend/tests/{conftest,test_email}.py` (+ tests adaptés) ; `frontend/src/app/admin/(app)/emails/page.tsx`, menu et alerte du tableau de bord ; `e2e/order.ts` (e-mail), `e2e/backoffice.spec.ts` ; docs 03 §1 et §8, 10-bilan, 10-guide-back-office. Correctif : règles mobile money de docs/02 renumérotées RG-70 à RG-76 (collision avec RG-50 à RG-54).
- Étape 11.3 : `docs/02-conception-fonctionnelle.md` §11 (RG-70 à RG-76, statuts, écrans), `docs/03-conception-technique.md` §7 (routes mobile money), `docs/09-deploiement.md` §9 (activer un prestataire réel, textes du site à changer), `docs/10-guide-back-office.md` (commandes payées, remboursement), `docs/10-bilan.md`. Textes publics du site **volontairement inchangés** (« paiement à la livraison ») : le mobile money reste désactivé en production tant qu'aucun prestataire n'est branché.
- Étape 11.2 : `frontend/src/app/(boutique)/commande/` (choix du paiement, redirection, `paiement/` page de retour et nouvel essai, `confirmee` « payée »), `frontend/src/app/paiement/simulation/` (faux prestataire), `frontend/src/components/{pay-button,order-view}.tsx`, panier, compte, back-office (onglet « En attente de paiement », moyen de paiement, livraison sans encaissement, remboursement d'un paiement reçu sur une commande annulée, bordereau), livreur (« rien à encaisser »), `src/lib/{types,format,schemas}.ts`, `e2e/paiement.spec.ts` + scénario mobile money dans `e2e/backoffice.spec.ts`, CI (`PAYMENT_PROVIDER=simulation` dans le job e2e), `backend/tests/conftest.py` (tests isolés du `.env` local).
- Étape 11.1 : `backend/app/modules/payments/providers.py`, `backend/app/modules/orders/{service,router,schemas,notify,jobs}.py`, migration `0003_mobile_money`, `backend/app/core/{config,csrf}.py`, `backend/app/main.py` (tâche d'expiration), panier et livreur, `backend/tests/test_mobile_money.py`.
- Étape 10 : `docs/10-bilan.md`, `docs/10-guide-back-office.md`, `docs/03-conception-technique.md` (§8, §12 à jour), `backend/app/core/images.py` (décodeurs limités).
- Étape 9 : `render.yaml`, `.github/workflows/backup.yml`, `docs/09-deploiement.md`, `backend/app/core/{config,storage}.py` (garde-fous de production, R2), `backend/app/modules/auth/deps.py` (`client_ip`), `backend/tests/test_production.py`, `frontend/src/lib/backend.ts`.
- `backend/app/scripts/seed_demo.py` — catalogue d'exemple fictif (+ comptes de test E2E si variables fournies) ; route `GET /admin/couriers` ; `variant_id` sur les lignes de commande.

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
| 2026-10-26 | CI GitHub (commit 6.3) | backend, frontend, e2e : verts |
| 2026-10-26 | 6.4 : `pytest` | 75/75 réussis |
| 2026-10-26 | 6.10 : `pytest` | 136/136 réussis |
| 2026-10-26 | 6.10 : démonstration réelle via le relais (base de dev, données supprimées, numérotation remise à PP-10001) | tableau de bord (CA 76 000, frais 1 500, panier moyen, taux 100 %, meilleures ventes, stocks bas, espèces chez les livreurs, messages) ; message de contact avec un fixe ; fiche client ; paramètres boutique ; journal d'audit |
| 2026-10-26 | 6.9 : `pytest` | 130/130 réussis |
| 2026-10-26 | 6.9 : démonstration réelle via le relais (base de dev, données supprimées, numérotation remise à PP-10001) | adresse au carnet ; échec « reportée » → nouvelle tentative (2) ; échec « injoignable » → 3e tentative refusée ; colis revenu contrôlé 1 bon / 1 fêlé → Retour +1, Perte tracée, paiement annulé ; historique client complet. Le script de nettoyage a d'abord échoué (ordre des suppressions), corrigé puis relancé : base vide |
| 2026-10-26 | 6.8 : `pytest` | 124/124 réussis |
| 2026-10-26 | 6.8 : démonstration réelle via le relais (base de dev, données supprimées, numérotation remise à PP-10001) | récapitulatif serveur 76 000 + 1 500 = 77 500 ; le livreur ne voit que sa livraison ; « livrée » refusée à 75 000, acceptée à 77 500 ; caisse interdite au livreur (403) ; remise de 77 000 refusée sans explication puis enregistrée avec écart −500 ; paiement « Remis » |
| 2026-10-26 | 6.7 : `pytest` | 118/118 réussis (dont 8 validations simultanées de la dernière unité : 1 commande, 7 refus ; relancé 5 fois) |
| 2026-10-26 | 6.7 : démonstration réelle via le relais (base de dev, données supprimées, numérotation remise à PP-10001) | total périmé → 409 avec nouveau total ; commande invité PP-10001, panier vidé ; double envoi → même commande ; stock réservé 2 ; suivi invité OK / mauvais téléphone 404 ; appel confirmé → Confirmée ; En livraison refusée sans livreur puis acceptée → sortie de stock ; annulation en route refusée ; e-mails client et boutique (console) |
| 2026-10-26 | 6.6 : `pytest` | 98/98 réussis |
| 2026-10-26 | 6.6 : démonstration réelle via le relais (base de dev, données supprimées ensuite) | cookie panier HttpOnly 90 j ; 2+2 sur un stock de 3 → 409 « max 3 » ; prix modifié → panier à jour ; création de compte → panier conservé ; parfum dépublié → ligne « indisponible », commande bloquée |
| 2026-10-26 | 6.5 : `pytest` | 89/89 réussis (dont 12 commandes simultanées sur le dernier flacon : 1 réussite, 11 refus ; relancé 5 fois) |
| 2026-10-26 | 6.5 : démonstration réelle via le relais (base de dev, données supprimées ensuite) | stock initial 6 ; entrée +10 ; ajustement sans motif refusé (422) ; ajustement −11 → disponible 5, alerte au tableau de bord et e-mail « Stock bas » (console) ; suppression d'un parfum avec historique refusée (409) |
| 2026-10-26 | 6.4 : démonstration réelle via le relais (base de dev, données supprimées ensuite) | connexion 2FA ; publication refusée sans contenance/image (409) ; JPEG 2400×3000 de 110 Ko → WebP 1600×2000 de 5 Ko ; recherche « demonstration » trouve « Démonstration » ; suppression → image 404 |
| 2026-10-26 | Étape 7 : backend `pytest` / frontend Vitest / lint / typecheck / build | 137/137 / 11/11 / OK / OK / 50 pages |
| 2026-10-26 | Étape 8 : backend `pytest`, `ruff`, `mypy` (local) | 137/137 réussis ; OK ; OK |
| 2026-10-26 | Étape 8 : CI GitHub run 40349531610 (commit d982476) | backend, frontend, e2e : verts ; **E2E 18/18 réussis** (9 parcours × mobile Pixel 7 + ordinateur), 0 échec, 0 relance |
| 2026-10-26 | Étape 9 : CI GitHub run 40355511225 (commit 5be97f8 ; le précédent était rouge : mypy sur un test, corrigé) | backend 149/149, frontend 11/11, E2E 18/18 : verts |
| 2026-10-26 | Étape 9 : backend `pytest`, `ruff`, `mypy` | 149/149 réussis (dont adresse client derrière relais, garde-fous de production, stockage R2 simulé) ; OK ; OK |
| 2026-10-26 | Étape 9 : relais Next.js → en-têtes reçus par le backend (serveur d'écho local) | `X-Forwarded-For` transmis tel quel, sans ajout → l'adresse du client est celle ajoutée par Render (ou Cloudflare) |
| 2026-10-26 | Étape 9 : démarrage `APP_ENV=production` en local | configuration incomplète → refus avec la liste des manques ; complète → santé 200, URL d'image sur le domaine R2 |
| 2026-10-26 | Étape 9 : `pg_dump` (format custom) → `pg_restore` dans une base temporaire | comptes identiques (parfums, commandes, mouvements, audits), migration 0002 et séquence conservées ; base temporaire supprimée |
| 2026-10-26 | Étape 9 : frontend lint / typecheck / Vitest / build avec `BACKEND_INTERNAL_URL=hôte:port` | OK / OK / 11/11 / relais `http://hôte:port/api/v1` |
| 2026-10-26 | Étape 10 : `pnpm audit` (frontend) | 0 vulnérabilité |
| 2026-10-26 | Étape 10 : `pip-audit` (dépendances de production du backend) | **37 vulnérabilités, toutes dans Pillow 12.3.0** (corrigées en 13.0.0, publiée le 2026-10-16) → décodeurs limités à JPG / PNG / WebP (`formats=`), test GIF / TIFF refusés ; montée de version reportée au 2026-10-30 |
| 2026-10-26 | Étape 10 : backend `pytest`, `ruff`, `mypy` (comme en CI) | 149/149 réussis ; OK ; OK |
| 2026-10-26 | 11.1 : migration 0003 (`upgrade`, `alembic check`, `downgrade 0002`, `upgrade`) | OK |
| 2026-10-26 | 11.1 : backend `pytest`, `ruff`, `mypy` (comme en CI) | 156/156 réussis (dont 7 mobile money) ; OK ; OK |
| 2026-10-26 | 11.1 : parcours réel via le relais Next.js (simulation) | PP-10002 « En attente de paiement » ; avis falsifié sans cookie → 401 ; échec → inchangé ; paiement → Confirmée / Payé ; mauvais jeton → 404 |
| 2026-10-26 | 11.2 : backend `pytest` (avec `PAYMENT_PROVIDER=simulation` dans `.env`), `ruff`, `mypy` | 156/156 (avant correctif de `conftest.py` : 4 échecs, les tests lisaient le `.env` local) ; OK ; OK |
| 2026-10-26 | 11.2 : frontend lint / typecheck / Vitest / build | OK / OK / 12/12 / OK |
| 2026-10-26 | 11.2 : E2E Playwright **en local** (nouveau poste macOS 26, Chromium disponible), base neuve, `CI=1` | **24/24 réussis**, 0 relance (12 parcours × mobile + ordinateur, dont mobile money : refus → nouvel essai → payé → suivi ; lien falsifié ; payée → livreur « rien à encaisser » → absente des encaissements). Rejoués sur la même base : échecs par limite de commandes par IP (429) et stock épuisé, attendus |
| 2026-10-26 | 11.2 : captures sur Pixel 7 (commande avec choix du paiement, page simulée, paiement en attente) | affichage correct |
| 2026-10-26 | 12 : backend `pytest`, `ruff`, `mypy` ; migration 0004 (`upgrade`, `alembic check`, `downgrade 0003`, `upgrade`) | 164/164 (8 nouveaux ; contrôle par mutation : nouveaux essais désactivés → 1 échec) ; OK ; OK ; OK |
| 2026-10-26 | 12 : frontend lint / typecheck / Vitest / build | OK / OK / 12/12 / OK |
| 2026-10-26 | 12 : E2E local, base neuve, `CI=1` | 24/24, 0 relance ; 18 e-mails mis en file, tous envoyés au 1er essai par la tâche de fond (console). Premier essai rouge : page E-mails sans rafraîchissement (parcours de 3 s < cycle de 5 s), corrigé par un rafraîchissement automatique |
| 2026-10-26 | CI GitHub run 40392680792 (commit 5eea38d : étapes 11.2 à 12) | backend 164/164, frontend 12/12, **E2E 24/24** : verts |
| 2026-10-26 | 13 : backend `pytest`, `ruff`, `mypy` ; migration 0005 (`upgrade`, `alembic check`, `downgrade 0004`, `upgrade`) | 171/171 (7 nouveaux, dont 8 commandes simultanées sur un code limité à 2 → 2 acceptées ; sans le verrou : échec 3 fois sur 3) ; OK ; OK ; OK |
| 2026-10-26 | 13 : frontend lint / typecheck / Vitest / build ; E2E local base neuve (`CI=1`, `ORDER_RATE_LIMIT=100`) | OK / OK / 12/12 / OK ; **26/26**, 0 relance ; capture Pixel 7 du récapitulatif avec code |
| 2026-10-26 | CI GitHub run 40404803776 (commit e7d6493 : étape 13) | backend 171/171, frontend 12/12, **E2E 26/26** : verts |
| — | E2E Playwright (ancien poste macOS 13) | jamais exécuté en local (Chromium indisponible sur macOS 13) : uniquement dans le job `e2e` de la CI |

## Étape 8 — matrice des parcours

Niveaux : **API** = tests d'intégration pytest sur une vraie base PostgreSQL ; **E2E** = Playwright dans un vrai navigateur (CI), sur mobile et ordinateur.

| Parcours | Couvert par | Résultat |
|---|---|---|
| Recherche d'un parfum | API `test_search_ignores_accents_and_case` ; E2E « recherche sans accents » | réussi |
| Ajout au panier | API `test_cart.py` ; E2E « commande sans compte » | réussi |
| Vérification du stock | API `test_stock.py` (dont 12 achats simultanés du dernier flacon), `test_cart.py` ; E2E « rupture de stock affichée » | réussi |
| Création et confirmation de commande | API `test_orders.py` (dont validations simultanées) ; E2E « commande sans compte » + back-office (Confirmée) | réussi |
| Paiement en test | — | **non applicable** : MVP en paiement à la livraison, aucun prestataire intégré. Encaissement espèces couvert (API `test_cash.py`, E2E remise en caisse) |
| Préparation et livraison | API `test_cash.py`, `test_delivery.py` ; E2E back-office → livreur → remise en caisse | réussi |
| Annulation | API `test_customer_orders_and_cancels`, `test_staff_cancellation_needs_a_reason` ; E2E « le client annule sa commande » | réussi |
| Remboursement (retour) | API `test_delivered_order_return_and_refund`, `test_failed_delivery_retry_then_return` | réussi en API ; **non exécuté en E2E** (écran réservé au Propriétaire, pas de compte Propriétaire de test) |
| Accès administrateur | API `test_staff.py` (2FA obligatoire) ; E2E connexion Gestionnaire avec code 2FA | réussi |
| Permissions | API : 45 assertions 401/403 ; E2E : client renvoyé de `/admin`, visiteur renvoyé vers la connexion | réussi |
| Gestion des erreurs | API : validation en français, CSRF, limitation des tentatives ; E2E : mauvais mot de passe, CGV non acceptées, suivi introuvable générique | réussi |
| Utilisation mobile | tous les E2E rejoués sur Pixel 7 | réussi |

## Problèmes connus / risques

- Refus et absences au paiement à la livraison ; argent liquide détenu par les livreurs.
- Notoriété d'une marque nouvelle : la qualité des photos et du contenu est déterminante.
- Réglementation des cosmétiques (étiquetage, composition, allergènes) : à vérifier avec un professionnel.
- Données personnelles (loi ivoirienne n° 2013-450, ARTCI) : à confirmer avec un juriste.
- Deux services à héberger (Next.js + FastAPI) : coût et complexité de déploiement plus élevés qu'un monolithe.
- macOS 13 du poste de développement : plus de paquets Homebrew précompilés, pas de Chromium Playwright. Contournements : uv via pip, Postgres.app, E2E en CI.
- ESLint 9 n'est plus maintenu ; passage à ESLint 10 quand les plugins de Next.js le supporteront.
- Images : stockage local en développement (`backend/media/`) ; R2 en production (code prêt, jamais testé contre un vrai compte R2).
- Adresse IP des clients (limites par IP) : réglée par `TRUSTED_PROXY_HOPS` ; valeur à confirmer en production (journal d'audit, docs/09 §4). Un attaquant qui contourne Cloudflare par l'URL `onrender.com` peut falsifier son adresse aux yeux des limites par IP.
- Base de production ouverte aux connexions externes (TLS + mot de passe généré) pour la sauvegarde GitHub Actions.
- Pas de Sentry ni de journaux JSON au MVP (journaux Render + notifications Render).
- Pillow 12.3.0 vulnérable (voir docs/10-bilan.md) : exposition réduite aux PNG envoyés par l'équipe ; montée en 13.0.0 prévue le 2026-10-30.
- Écarts de l'étape 7 par rapport à la conception : composants maison à la charte au lieu de shadcn/ui (pas d'installation de code externe, moins de dépendances) ; `<img>` au lieu de `next/image` (images déjà optimisées en WebP par le backend, compatible R2) ; pas de QR code pour la 2FA (clé + lien `otpauth://`).
- CI E2E lente (≈ 12 min) : le téléchargement des paquets système de Chromium depuis le miroir Ubuntu est très lent ; les tests eux-mêmes prennent quelques secondes. Piste étape 9 : image Docker officielle Playwright ou cache.
- Base de développement : contient le catalogue d'exemple (fictif) et les comptes `gestion-e2e@exemple.com` / `livreur-e2e@exemple.com` de vérification locale.
- `uv` n'est pas dans le PATH par défaut : `export PATH="$HOME/Library/Python/3.9/bin:$PATH"`.

## Prochaine action

Étapes 11 à 13 poussées (CI verte, run 40404803776). Reportés par le porteur : choix du prestataire de mobile money (docs/09 §9) et mise en ligne. Mise en ligne en fin de projet, quand le porteur fournit le domaine et les comptes et tranche la préproduction : `docs/09-deploiement.md` §3, chaque action publique ou payante avec son accord.
À partir du 2026-10-30 : passer Pillow 12.3.0 → 13.0.0 (vulnérabilités, voir docs/10-bilan.md).

Environnement local : macOS 13, Node 22, pnpm 11 (Corepack), Python 3.13 via uv (`~/Library/Python/3.9/bin/uv`), PostgreSQL 17.11 via Postgres.app ; pas de Docker.
Nouveau poste (2026-10-26) : macOS 26.1, Node 25, Homebrew : `uv`, `pnpm`, `postgresql@17` (`brew services start postgresql@17`, binaires dans `/opt/homebrew/opt/postgresql@17/bin`) ; Chromium Playwright installé (E2E possibles en local). `backend/.env` : `PAYMENT_PROVIDER=simulation`. `gh` authentifié (compte Jihem225).
