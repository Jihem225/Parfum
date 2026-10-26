# Bilan de livraison — Projet Parfums (MVP)

État au 2026-10-26 : **MVP complet et testé, pas encore en ligne.** La mise en ligne attend le domaine et les comptes Render, Cloudflare et Resend (voir `docs/09-deploiement.md`).

## Où trouver chaque livrable

| Livrable | Emplacement |
|---|---|
| Code source | https://github.com/Jihem225/Parfum (`backend/` FastAPI, `frontend/` Next.js) |
| Installation (poste de développement) | `README.md` |
| Documentation technique | `docs/03-conception-technique.md` (architecture, modèle de données, API, sécurité) ; API interactive : `/api/v1/docs` |
| Règles métier et parcours | `docs/02-conception-fonctionnelle.md`, maquettes `docs/04-maquettes.md` |
| Documentation du back-office | `docs/10-guide-back-office.md` |
| Tests et résultats | `SUIVI.md` (« Tests exécutés », « Étape 8 — matrice des parcours ») ; CI GitHub à chaque envoi |
| Variables d'environnement | `docs/03-conception-technique.md` §12 ; `backend/.env.example`, `frontend/.env.example`, `render.yaml` |
| Sauvegarde et restauration | `docs/09-deploiement.md` §6 ; `.github/workflows/backup.yml` |
| Procédure de mise à jour et retour arrière | `docs/09-deploiement.md` §8 |
| Déploiement | `render.yaml`, `docs/09-deploiement.md` |

## Ce que fait le MVP

**Boutique**
- Catalogue par collections, recherche sans accents, filtres et tri.
- Fiches produit 30/50/100 ml avec stock affiché.
- Panier visiteur ou client, commande sans compte, confirmation, suivi par numéro + téléphone.
- Paiement à la livraison ; mobile money prêt (étape 11), à activer avec un prestataire réel.
- Compte client : adresses, commandes, annulation.
- Contact, pages d'information, sitemap.

**Back-office**
- Tableau de bord.
- Commandes : appels, préparation, livreur, échecs, retours, impression.
- Catalogue et images, stock (mouvements, alertes).
- Encaissements par livreur et remises de caisse.
- Clients, messages, paramètres et communes, collaborateurs.
- Journal d'audit.
- Double authentification obligatoire pour le Propriétaire et les Gestionnaires.

**Espace livreur** : ses livraisons, « livrée et encaissée », déclaration d'échec.

**Garanties**
- Pas de survente : stock réservé de façon atomique, vérifié par des tests d'achats simultanés.
- Un double envoi ne crée pas deux commandes.
- Prix et total recalculés par le serveur.
- Protection CSRF, cookies `httpOnly`, mots de passe Argon2.
- Limitation des tentatives.
- Aucune action du back-office sans trace.

## Tests (dernier état : CI run 40355511225)

| Suite | Résultat |
|---|---|
| Backend pytest sur PostgreSQL réel | 149/149 réussis |
| Frontend Vitest | 11/11 réussis |
| Parcours E2E Playwright (mobile + ordinateur) | 18/18 réussis |
| Lint, typage strict (mypy, TypeScript), build | OK |
| File d'envoi des e-mails (étape 12, local) | backend 164/164 (dont 8 sur la file : transaction, nouveaux essais, abandon, refus, purge, renvoi), Vitest 12/12, E2E 24/24 (e-mail envoyé par la tâche de fond et visible au back-office) |
| Mobile money (étape 11, local, commit 2c6d568) | backend 156/156, Vitest 12/12, E2E 24/24 (dont 3 parcours mobile money × 2 appareils), avec le prestataire de simulation |
| Non exécutés | paiement avec un vrai prestataire (pas encore choisi) ; écran de retour / remboursement dans le navigateur (couvert en API) ; vrai téléphone et Safari ; charge ; services réels R2, Resend et Render (comptes à créer) |

## Limites connues

- **Paiement** : en production, à la livraison uniquement tant qu'aucun prestataire de mobile money n'est branché. Le parcours complet existe et est testé avec un prestataire simulé ; brancher le vrai : `docs/09-deploiement.md` §9. La carte bancaire reste à faire.
- **Contenus provisoires** : nom « Projet Parfums », préfixe `PP`, textes légaux marqués « [À compléter …] » (CGV, mentions légales, confidentialité : à faire relire par un juriste), photos.
- **Hors MVP** : avis, favoris, codes promo, bannières, newsletter, paniers abandonnés, permissions fines, multi-pays.
- **Exploitation** :
  - pas de Sentry ni de journaux JSON : journaux et notifications de Render uniquement ;
  - e-mails : file d'envoi avec nouveaux essais depuis l'étape 12 ; la tâche d'envoi tourne dans le processus de l'API (un redémarrage la relance, rien n'est perdu) ;
  - images R2 sans sauvegarde séparée.
- **Sécurité réseau** :
  - la base de production accepte les connexions externes (TLS + mot de passe généré) pour la sauvegarde ;
  - un client qui contourne Cloudflare par l'adresse `onrender.com` peut fausser son IP vis-à-vis des limites par IP.
- **Écarts de conception** : composants maison au lieu de shadcn/ui ; `<img>` au lieu de `next/image` ; activation de la double authentification par clé et lien, sans QR code ; règle « 3 appels » sans fenêtre de 48 h dans le code (consigne dans le guide).
- **Pillow 12.3.0** (traitement des photos) : 37 vulnérabilités connues, corrigées en 13.0.0 (publiée le 2026-10-16).
  - Le code n'ouvre plus que JPG, PNG et WebP. Les failles des autres formats (dont une exécution de code via FlashPix) sont donc inatteignables.
  - Restent deux lenteurs ou surconsommations mémoire possibles via un PNG piégé, envoyé uniquement par un Gestionnaire ou le Propriétaire connecté.
  - **Passer à Pillow 13 à partir du 2026-10-30** (règle des 14 jours du projet) et relancer les tests.
- **Outillage** :
  - tests E2E : en CI, et en local depuis le passage au poste macOS 26 (2026-10-26) ;
  - CI parfois lente (miroir Ubuntu pour Chromium) ;
  - ESLint 9 à faire passer en 10 quand Next.js le permettra.

## Recommandations de maintenance

| Fréquence | Action |
|---|---|
| Chaque jour | Vérifier sur le tableau de bord les commandes en attente, les stocks bas et les espèces détenues par les livreurs. |
| Chaque semaine | Vérifier que la sauvegarde GitHub (Actions → Sauvegarde) est verte. Rapprocher les remises de caisse. |
| Chaque mois | Mises à jour de sécurité : `pnpm audit` (frontend) et, dans `backend/`, `uv export --frozen --no-dev --no-hashes --no-emit-project > /tmp/req.txt && uvx pip-audit -r /tmp/req.txt`, mise à jour des dépendances sur une branche, CI verte, puis fusion. Relire le journal d'audit. Désactiver les comptes des collaborateurs partis. |
| Chaque trimestre | Restaurer une sauvegarde dans une base temporaire (`docs/09-deploiement.md` §6). Revoir les tarifs Render et R2 et le volume des images. |
| Avant chaque évolution | Garder les migrations compatibles avec la version précédente (ajouter, puis supprimer dans une version ultérieure) ; ne jamais désactiver la CI pour déployer. |

**Évolutions suggérées, par ordre d'utilité :**
1. Brancher le prestataire de mobile money (`docs/09-deploiement.md` §9).
2. Sentry.
3. Codes promo.
4. Préproduction quand l'équipe grandit.
