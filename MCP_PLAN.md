# Plan exécuté : rencontres dynamiques et agents

## Architecture livrée

Le navigateur et l'adaptateur MCP utilisent un service Python local commun.
Ce service possède un worker melonDS isolé avec IPC dédié, révisions et verrou
de contrôle. Les logs natifs restent dans un fichier séparé du protocole MCP.

Une coque ROM fixe démarre une scène native d'attente. Le pont remplace ses
emplacements SSD/SST bornés et l'en-tête d'équipe domicile en RAM. Les routines
natives retirent l'ancien effectif, ajoutent le nouveau, affichent six répliques
entre les capitaines puis lancent le match sélectionné. Les deux équipes de
cette livraison sont Occulte et Zeus, dans les deux sens. Le retour au salon
utilise le checkpoint initial du même worker : aucune reconstruction ni
relecture de ROM par affiche.

L'organisateur Codex résout la demande du chat et rédige le dialogue. Le joueur
visuel est un second agent, invoqué uniquement sur demande. Il observe les deux
écrans et choisit des commandes DS validées. L'émulation attend chaque décision.
L'utilisateur peut arrêter l'agent et reprendre le contrôle manuel.

## Contrats

- Les identités ROM et cœur sont vérifiées avant d'utiliser le profil mémoire.
- Une action directe exige la révision courante et le bon détenteur du contrôle.
- Les segments d'entrée sont limités à 120 frames ; le tactile utilise les
  coordonnées de l'écran inférieur. Le cœur échantillonne aussi le relâchement.
- La préparation exige la scène native d'attente, et contrôle les limites des
  buffers avant toute écriture. Une lecture de vérification suit les écritures.
- Les checkpoints sont éphémères, limités à huit et liés au processus courant.
- Les jobs asynchrones exposent progression, erreurs, annulation et fin.
- Une affirmation visuelle de l'agent ne fabrique jamais un résultat natif.

Le module `dynamic_protocol.py` conserve un prototype de boîte aux lettres
versionnée avec CRC. Le chemin livré utilise les buffers SSD/SST natifs mesurés,
sans prétendre qu'un hook ARM9 consommant ce prototype aurait été installé.

## Livraison et vérification

Voir `DELIVERY.md` pour lancer l'application, `WEB_AND_MCP.md` pour le client MCP,
et `DELIVERY_VERIFICATION.md` pour les essais réellement effectués.
Les simulations statistiques, prédictions et extensions à d'autres équipes
restent hors du périmètre de cette livraison.
