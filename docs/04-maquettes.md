# Maquettes UI/UX — « Projet Parfums »

Version 1 — 2026-10-26 — statut : **proposée, en attente de validation**.

- Canevas interactif (privé, compte du porteur) : https://claude.ai/artifact/1bF31hbjmR5b2TqJgMDrXr
- Sources des maquettes : [`docs/maquettes/`](maquettes/) (copie du canevas, format `.dc.html`)

Noms de parfums, prix, clients et chiffres : **exemples fictifs**. Les flacons dessinés remplacent les photos produits à venir.

## Écrans

| # | Écran | Format | Interactions dans la maquette |
|---|---|---|---|
| 1 | Accueil | mobile 390 px | liens vers catalogue, fiche, panier |
| 2 | Catalogue | mobile | recherche, tri, filtres actifs, badges de stock |
| 2b | Filtres | mobile (panneau) | genre, familles, prix, contenance, disponibilité |
| 3 | Fiche produit | mobile | choix de la contenance (prix et stock changent), quantité plafonnée au stock |
| 4 | Panier | mobile | quantités (max 5), retrait, totaux recalculés |
| 5 | Commande (sans compte) | mobile | commune → frais et total ; CGV obligatoires ; écran de confirmation |
| 6 | Connexion / inscription | mobile | onglets ; exemple d'état d'erreur |
| 7 | Espace client — suivi | mobile | chronologie des statuts |
| 8 | Admin — tableau de bord | ordinateur, s'adapte au mobile | — |
| 9 | Admin — produits | ordinateur | liste + fiche d'édition, contenances et stock |
| 10 | Admin — commandes | ordinateur | file « À confirmer », résultat d'appel → action |

## Charte provisoire

| Élément | Valeur |
|---|---|
| Fond | Porcelaine `#FAFAF8` ; surfaces `#F1EEE9` ; admin `#F4F2EE` |
| Texte / encre | `#1A1613` ; secondaire `#6B635B` ; filets `#E2DDD5` |
| Accent | Safran `#9A5B13` (badges, alertes de stock, mise en avant) |
| États | Succès `#2F6B4F` ; erreur `#7A2C1F` ; information `#27466E` |
| Titres | Bodoni Moda (Google Fonts) |
| Texte | Manrope (Google Fonts) |
| Produits | Fond teinté par la couleur du jus de chaque parfum |
| Boutons | Encre pleine, angles quasi droits, 52 px de haut en mobile (cibles ≥ 44 px) |

Contrastes calculés le 2026-10-26 pour les 18 couples texte / fond de la charte : tous entre 5,1:1 et 12:1 (minimum requis 4,5:1). Exception à corriger au développement : la carte « Rupture de stock » du catalogue est estompée par transparence, ce qui fait passer son texte sous le seuil. La charte sera remplacée ou ajustée dès que le nom, le logo et les couleurs de la marque seront connus.
