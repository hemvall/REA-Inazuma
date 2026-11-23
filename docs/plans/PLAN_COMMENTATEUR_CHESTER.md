# Chester Horse Junior — Commentateur IA

> Document historique. Voir le [commentaire de match actuel](../guides/WEB_AND_MCP.md#commentaire-de-match).

## Première version

Activez **Commentaire vocal** sous les commandes du terrain. Le commentaire est désactivé à l’ouverture du salon. Le curseur règle le volume des prochaines répliques et le niveau zéro coupe la voix en cours. Le navigateur utilise une voix française du système. En son absence, les annonces restent lisibles sous les commandes.

Le worker relève les changements de porteur et de possession, les duels, les tirs
repérés par les écrans de blocage ou du gardien, la mi-temps et la reprise, en plus
des buts et du résultat. Il échantillonne aussi pendant la lecture continue et
l’avance du pilote. Les annonces décrivent le changement de porteur même lorsque
le jeu ne permet pas de confirmer le geste qui l’a provoqué.

LM Studio rédige une courte réaction originale dans le registre du direct
sportif, à partir de l’annonce et de la dernière réaction du même type. Le score
et les faits restent dans l’annonce produite par le worker. Si le modèle ne livre
pas de phrase valide dans le délai, le salon lit cette annonce seule.

## Objectif

Faire parler Chester Horse Junior pendant les vrais matchs d’InazumIA. La première version cible le salon web, en français, avec une voix de synthèse originale de commentateur sportif énergique. Elle accompagne les matchs joués à la manette ou délégués à l’agent joueur.

## Parcours joueur

1. Avant le coup d’envoi, activer **Commentaire vocal** dans le salon. Ce clic autorise la lecture audio dans le navigateur.
2. Chester annonce l’affiche, réagit aux buts confirmés et annonce le résultat officiel. Ses phrases restent courtes et espacées pour laisser entendre le jeu.
3. Le joueur peut régler le volume du commentaire ou le couper pendant le match. Une option affiche la réplique en sous-titre.

## Événements de match

- Réutiliser les observations du worker melonDS via `observe_match` et les transitions du service de session. Construire les événements à partir de l’identifiant du match, de la frame et de l’état natif validé.
- Commencer par trois événements fiables : début de match, hausse confirmée du score, résultat natif. Un but annonce l’équipe et le score. Ajouter le nom du buteur, les tirs, les arrêts et les duels après validation de leurs signaux respectifs.
- À la connexion en cours de match ou après restauration d’un checkpoint, prendre l’état courant comme référence. Dédupliquer les événements dans une même séquence de jeu, réinitialiser la file lors d’un retour en arrière et écarter les répliques devenues obsolètes.

## Voix et génération

L’[essai vocal de Chester](chester-essai-voix.mp3) illustre l’intention de jeu
avec la voix de synthèse [Tom de Piper](https://huggingface.co/rhasspy/piper-voices/tree/main/fr/fr_FR/tom/medium).
Le salon utilise une voix française disponible dans le navigateur et ajuste
le débit et la hauteur selon l’action.

- Définir une personnalité éditoriale : enthousiaste, précise, formulations originales et une phrase par intervention. Fournir à l’IA uniquement les faits confirmés et un court historique des interventions. Exemple : « Et ça rentre pour Raimon ! Deux à un, le match bascule ! »
- Pour un but ou un résultat, faire prononcer le score et les noms d’équipe à partir du texte produit par le serveur. L’IA peut ajouter une réaction courte. Si sa réponse tarde, utiliser la formule prédéfinie.
- Commencer par la synthèse vocale du navigateur, valider les voix françaises sur les navigateurs utilisés et vérifier la prononciation des équipes. Évaluer ensuite une voix dédiée si la disponibilité ou le rendu varie trop selon la machine. Si l’audio est indisponible, afficher les sous-titres.
- Traiter la génération et l’audio hors de la boucle d’émulation. Jouer une phrase à la fois. Prioriser les buts et le résultat, supprimer les phrases périmées et interrompre la voix à la pause, à la coupure du commentaire ou à la fermeture du match. Reprendre à partir de l’état courant.

## Ordre de réalisation

1. Rejouer des observations enregistrées pour valider la détection des événements et leur déduplication.
2. Brancher le bouton, la file de lecture, les sous-titres et des annonces prédéfinies. Tester la voix pendant un vrai match.
3. Ajouter la variation par IA et le repli sur les annonces prédéfinies. Mesurer le délai entre la confirmation native et le début de la phrase. Viser un départ sous deux secondes pour un but, avec repli anticipé si le modèle est lent.
4. Étendre le vocabulaire aux actions supplémentaires après vérification dans melonDS.

## Critères de livraison

- Un match joué et un match délégué produisent des annonces vocales cohérentes avec les événements réellement observés.
- Deux buts rapprochés, des observations répétées et une reconnexion ne déclenchent ni doublons ni annonce périmée. Le résultat officiel est annoncé exactement une fois par séquence de jeu.
- Pause, reprise, retour au local et restauration d’un checkpoint laissent la file audio dans l’état attendu.
- Une indisponibilité du modèle ou de la synthèse vocale laisse les contrôles du match réactifs et déclenche le repli prévu.

## Références

- [Salon et observation du match](../guides/WEB_AND_MCP.md)
- [Observation du worker](../../src/match_actions.py)
- [Parcours de match et retour au Club](../guides/CLUB_FRIENDLIES.md)
