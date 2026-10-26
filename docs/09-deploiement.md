# Déploiement et exploitation

Cible validée à l'étape 3 : **Render (Francfort) + Cloudflare (DNS, HTTPS, R2) + Resend**, ≈ 20 $ / mois + domaine.
Les prix sont à revérifier sur les pages officielles au moment d'ouvrir les comptes.

## 1. Ce que contient le dépôt

| Fichier | Rôle |
|---|---|
| `render.yaml` | Plan Render : base PostgreSQL 17, API FastAPI, site Next.js, tous en région Francfort. Déploiement automatique **uniquement si la CI est verte** ; migrations Alembic appliquées avant le démarrage de la nouvelle version. |
| `.github/workflows/ci.yml` | Lint, typage, tests backend (PostgreSQL réel), tests frontend, build, parcours E2E. |
| `.github/workflows/backup.yml` | Sauvegarde quotidienne de la base vers un compartiment R2 privé (inactive tant que les secrets ne sont pas saisis). |
| `backend/app/core/config.py` | Refuse de démarrer en production si : cookies non sécurisés, origine non HTTPS, `SECRET_KEY` trop court, stockage R2 absent, `TRUSTED_PROXY_HOPS` absent. |

## 2. Environnements

- **Production** : les trois services Render ci-dessus.
- **Test** : la CI GitHub (base PostgreSQL jetable, catalogue fictif, parcours E2E) à chaque envoi sur `main`.
- **Préproduction** : non créée par défaut (≈ +20 $ / mois). Pour l'ajouter : dupliquer `render.yaml` avec d'autres noms (`parfums-staging-*`) et une branche dédiée.

## 3. Première mise en ligne (pas à pas)

Chaque étape marquée ⚠ est publique ou payante : elle se fait avec l'accord du porteur.

1. **Domaine** ⚠ : acheter le domaine (`.ci` ou `.com`) et le confier à Cloudflare (serveurs DNS de Cloudflare).
2. **Cloudflare R2** ⚠ :
   - compartiment `parfums-images`, public via le domaine `images.<domaine>` (pas l'URL `r2.dev`, limitée) ;
   - compartiment `parfums-backups`, **privé**, avec une règle de cycle de vie « supprimer après 30 jours » ;
   - deux jetons API S3, chacun limité à son compartiment (lecture / écriture).
3. **Render** ⚠ : *New → Blueprint*, choisir le dépôt GitHub, puis saisir les valeurs demandées (`sync: false`) :

   | Service | Variable | Valeur |
   |---|---|---|
   | parfums-api | `FRONTEND_ORIGIN` | `https://<domaine>` |
   | parfums-api | `S3_ENDPOINT_URL` | `https://<id-compte>.r2.cloudflarestorage.com` |
   | parfums-api | `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | compartiment et jeton des images |
   | parfums-api | `S3_PUBLIC_BASE_URL` | `https://images.<domaine>` |
   | parfums-api | `RESEND_API_KEY`, `EMAIL_FROM`, `SHOP_NOTIFICATION_EMAIL` | voir étape 5 |
   | parfums-web | `NEXT_PUBLIC_SITE_URL` | `https://<domaine>` |

   `SECRET_KEY` est générée par Render ; `DATABASE_URL` et `BACKEND_INTERNAL_URL` sont reliées automatiquement.
4. **Domaine du site** : dans Render, ajouter `<domaine>` et `www.<domaine>` au service `parfums-web`, puis créer les enregistrements DNS indiqués dans Cloudflare.
   - Une fois le certificat Render émis : passer les enregistrements en « proxied » (nuage orange), SSL/TLS en **Full (strict)**.
   - Passer alors `TRUSTED_PROXY_HOPS` à **2** sur `parfums-api` (Cloudflare ajoute un relais).
5. **E-mails (Resend)** ⚠ : vérifier le domaine (enregistrements DNS fournis par Resend, à créer dans Cloudflare), créer une clé API, puis renseigner `EMAIL_FROM` (ex. `Projet Parfums <commandes@<domaine>>`).
6. **Premier Propriétaire** : onglet *Shell* du service `parfums-api` :
   `.venv/bin/python -m app.scripts.create_owner <e-mail>`, puis connexion sur `/admin` et activation de la double authentification.
7. **Sauvegarde** : dans GitHub, *Settings → Secrets and variables → Actions*, créer :
   - `BACKUP_DATABASE_URL` (URL **externe** de la base, page de la base dans Render) ;
   - `R2_ENDPOINT` ;
   - `R2_BACKUP_BUCKET` (`parfums-backups`) ;
   - `R2_BACKUP_ACCESS_KEY_ID` et `R2_BACKUP_SECRET_ACCESS_KEY`.

   Lancer ensuite *Actions → Sauvegarde → Run workflow* et vérifier le fichier dans R2.

## 4. Vérifications après mise en ligne

- [ ] `https://<domaine>/api/v1/health` répond `{"status":"ok","database":"ok"}`.
- [ ] Le cadenas HTTPS est présent sur `<domaine>` et `images.<domaine>`.
- [ ] Un produit créé avec une photo l'affiche depuis `images.<domaine>`.
- [ ] Une commande test reçoit ses e-mails (client et boutique), puis est annulée depuis le back-office.
- [ ] **Journal d'audit** : la colonne IP de votre connexion montre **votre** adresse publique.
  - Si c'est une adresse Cloudflare ou Render, `TRUSTED_PROXY_HOPS` est faux : sinon, toutes les limites « par IP » (10 commandes / heure…) deviennent communes à tous les clients.
- [ ] La sauvegarde manuelle (§3.7) a produit un fichier, **restauré avec succès** dans une base temporaire (§6).

## 5. Secrets

- Stockés uniquement dans Render (variables d'environnement) et GitHub (secrets Actions), jamais dans le dépôt.
- Rotation : régénérer la valeur chez le fournisseur, la remplacer dans Render ou GitHub, puis redéployer.
- **Ne changer `SECRET_KEY` qu'en cas de fuite.** Elle chiffre les secrets de double authentification : après un changement, Propriétaires et Gestionnaires ne peuvent plus se connecter.
  - Il faut alors vider leur secret depuis le Shell de `parfums-api` : `UPDATE users SET totp_secret = NULL WHERE role IN ('OWNER','MANAGER');` via `psql "$DATABASE_URL"`.
  - Chacun réactive ensuite sa double authentification.

## 6. Sauvegardes et restauration

- **Render** : sauvegardes automatiques de la base (rétention et restauration à un instant donné selon l'offre : à vérifier à l'ouverture du compte).
- **Indépendante** : `pg_dump` quotidien (format custom) vers `parfums-backups`, conservé 30 jours.
- Restauration d'un export (testée le 2026-10-26 sur une base temporaire : comptes identiques, migration et numérotation des commandes conservées) :

  ```bash
  createdb parfums_restauration
  pg_restore --no-owner --no-acl --exit-on-error -d parfums_restauration parfums-AAAA-MM-JJTHHMM.dump
  ```

  Pour remettre en service : créer une nouvelle base Render, y restaurer l'export, pointer `DATABASE_URL` de `parfums-api` dessus, redéployer.
- Images : R2 n'est pas sauvegardé à part au MVP (fichiers jamais modifiés ; perte = rechargement des photos).

## 7. Journaux et santé

- Journaux : onglet *Logs* de chaque service Render (sortie standard). Aucun mot de passe ni jeton n'y est écrit.
- Santé : Render interroge `/api/v1/health` (API, vérifie la base) et `/robots.txt` (site) et redémarre un service qui ne répond plus.
- Alertes : activer les notifications e-mail de Render (échec de déploiement, service indisponible).

## 8. Mises à jour et retour arrière

- **Mise à jour** : envoi sur `main` → CI → si verte, Render construit, applique les migrations puis bascule sans coupure.
- **Retour arrière du code** : Render → service → *Events* → *Rollback* sur le déploiement précédent.
- **Migrations** : écrites pour rester compatibles avec la version précédente du code (ajouts d'abord, suppressions dans une version ultérieure). Un retour arrière ne défait donc pas la migration.
- **Données** : restauration (§6) seulement en dernier recours ; les commandes passées depuis la sauvegarde seraient perdues.
