# Guide du back-office

Pour le Propriétaire, les Gestionnaires et les livreurs. Adresse : `https://<domaine>/admin` (livreurs : `/livreur`).

## Se connecter

- **Propriétaire et Gestionnaire** : e-mail, mot de passe, puis le code à 6 chiffres de l'application d'authentification (Google Authenticator, Microsoft Authenticator…).
- **Première connexion** : le back-office demande d'activer la double authentification.
  1. Ajoutez la clé affichée dans l'application d'authentification.
  2. Saisissez le code pour confirmer.
- **Téléphone perdu** : le Propriétaire va dans **Collaborateurs → Réinitialiser la 2FA** de la personne, qui la réactive à sa prochaine connexion.
  - Si c'est le seul Propriétaire qui a perdu son téléphone, il faut une intervention technique (voir `docs/09-deploiement.md` §5).
- **Livreurs** : e-mail et mot de passe, sans code.

## Rôles

| Rôle | Peut |
|---|---|
| Propriétaire | tout, plus : **Boutique et livraison**, **Collaborateurs**, **Journal d'audit**, retour d'une commande livrée, remboursement d'un paiement mobile money |
| Gestionnaire | commandes, produits, collections, stock, encaissements, clients, messages |
| Livreur | voir **ses** livraisons, déclarer « livrée et encaissée » ou un échec |

## Traiter une commande (chaque jour)

Le **Tableau de bord** indique combien de commandes attendent à chaque statut. Dans **Commandes**, ouvrez la commande.

1. **En attente de confirmation : appeler le client.** Notez le résultat de l'appel :
   - **Confirmée** : la commande passe à « Confirmée ».
   - **Pas de réponse** : rappelez plus tard. Après 3 appels sans réponse, le back-office propose d'annuler. Espacez-les sur environ 48 h.
   - **Le client annule** : la commande est annulée et le stock libéré.
2. **Passer en préparation**, puis imprimer le **Bon de préparation** (et le **Bordereau** à coller sur le colis).
3. **Confier au livreur** : choisissez le livreur. Le stock sort à ce moment-là.
4. **Le livreur** livre, encaisse le montant exact affiché (**Total · espèces à encaisser**), puis appuie sur **Livrée et encaissée** dans son espace.
   - Si le livreur n'a pas son téléphone, le Gestionnaire peut le faire depuis la commande.
5. **Échec de livraison** (client injoignable, refus, adresse introuvable, livraison reportée) :
   - injoignable ou reportée : **Nouvelle tentative de livraison**, deux tentatives au maximum ;
   - refus ou adresse introuvable, ou deux tentatives déjà faites : le colis revient à la boutique. Enregistrez-le comme un retour (ci-dessous), sans remboursement.

**Annuler** : possible tant que la commande n'est pas partie en livraison, avec un motif obligatoire dans « Note ou motif ». Le client peut aussi annuler lui-même depuis son compte, dans les mêmes conditions.

## Commandes payées par mobile money

Seulement quand le paiement en ligne est activé (voir `docs/09-deploiement.md` §9). Sur la commande, la ligne **Paiement** indique le moyen : « Espèces à la livraison » ou « Mobile money ».

- **En attente de paiement** : le client n'a pas encore payé. Rien à faire : la commande passe seule à **Confirmée** au paiement, ou est annulée 30 minutes après sa création (stock libéré).
- **Confirmée** et « Mobile money · Payé » : **pas d'appel de confirmation**. Passez directement en préparation, puis confiez au livreur comme d'habitude.
- **Livraison** : le livreur voit « Déjà payée · rien à encaisser » et confirme simplement la remise ; le bordereau l'indique aussi. Ces commandes n'apparaissent pas dans les Encaissements.
- **Paiement à rembourser** : une commande payée puis annulée (par le client, par vous, ou paiement arrivé après le délai) affiche cette carte. Dans ce dernier cas, la boutique reçoit aussi un e-mail « À rembourser ».
  1. Remboursez le client depuis le tableau de bord du prestataire.
  2. Le Propriétaire saisit le **Montant remboursé** (et la référence du remboursement en note), puis **Enregistrer le remboursement**. C'est définitif.
- **Retour d'une commande livrée payée par mobile money** : comme ci-dessous, le montant est remboursé chez le prestataire au lieu d'espèces.

## Récupérer l'argent des livreurs (Encaissements)

La page liste, par livreur, les espèces qu'il détient et les commandes concernées.

1. Comptez l'argent remis, saisissez le **Montant reçu**, puis **Enregistrer la remise**.
2. En cas d'écart, une **explication est obligatoire**. La remise ne peut plus être modifiée ensuite.

## Retour d'un colis

Dans la commande : **Retour client et remboursement** (colis revenu après un échec de livraison ; ou commande livrée, Propriétaire uniquement).

1. Pour chaque article, indiquez combien reviennent **En stock** (revendables) et combien sont **Perdus** (cassés…).
2. Commande livrée : indiquez le **Montant remboursé en espèces**. Le remboursement n'est possible qu'une fois l'argent de cette commande remis en caisse.
3. Cette action est définitive.

## Produits

1. **Produits → Nouveau** : nom, collection, famille, genre, description et notes (tête, cœur, fond).
2. **Contenances** : volume (30, 50, 100 ml), prix en FCFA, seuil d'alerte, stock initial.
3. **Images** : ajoutez des photos (elles sont réduites et converties automatiquement), puis ordonnez-les avec **Avancer** / **Reculer**. La première photo est l'image principale.
4. **Publier** : il faut au moins une contenance active et une image.
   - **Dépublier** retire le parfum de la boutique.
   - **Archiver** le range.
   - Un parfum déjà vendu ne peut pas être supprimé : archivez-le.

## Stock

- **Entrée (réception)** : à chaque livraison du fournisseur.
- **Ajustement (+ ou −)** : inventaire, casse… Le motif est obligatoire. Une quantité négative retire du stock.
- **Physique** = flacons en boutique. **Réservé** = commandés, pas encore partis. **Disponible** = ce que les clients peuvent acheter.
- **Stock bas uniquement** liste ce qui passe sous le seuil d'alerte. Un e-mail d'alerte est aussi envoyé à l'adresse de la boutique.
- **Historique** : chaque mouvement, avec son auteur et sa commande.

## Autres pages

- **Clients** : coordonnées, commandes et total livré par client.
- **Messages** : formulaire de contact du site ; marquez-les « traité ».
- **Boutique et livraison** (Propriétaire) :
  - téléphone, WhatsApp, e-mail, adresse et horaires affichés sur le site ;
  - **communes desservies** avec leurs frais et délais. Décochez « Desservie » pour suspendre une commune.
- **Collaborateurs** (Propriétaire) : créer un Gestionnaire ou un livreur avec un mot de passe provisoire, désactiver un compte. Le dernier Propriétaire ne peut pas être retiré.
- **Journal d'audit** (Propriétaire) : qui a modifié quoi, quand, et depuis quelle adresse.

## Règles à connaître

- Au plus 5 flacons d'un même parfum par commande. Total maximum en paiement à la livraison : 300 000 FCFA (pas de plafond en mobile money).
- Les prix affichés au client sont recalculés au moment de valider sa commande. Si un prix a changé entre-temps, le client voit le nouveau total avant de confirmer.
