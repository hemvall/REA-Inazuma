# Recrutement spécial !

## Objectif

Ajouter dans le salon InazumIA un agent capable de discuter avec le joueur, de transformer ses idées en fiche de recrue fictive, puis de l’inscrire dans l’effectif jouable après confirmation. La première version cible le profil Club du lanceur web, dans une partie isolée.

## Parcours

1. Le joueur ouvre **Recrutement spécial !** depuis le salon, au local et hors match.
2. Il décrit sa recrue en français, par exemple « Une gardienne rapide spécialisée dans les arrêts réflexes ». L’agent propose un nom et complète le poste, les stats, les techniques, le portrait et le sprite. Il demande les précisions nécessaires et peut réviser la fiche sur plusieurs messages.
3. Le salon affiche la fiche prévisualisée, les éventuels ajustements nécessaires pour le moteur DS et la place disponible dans l’effectif. Le joueur peut corriger, annuler ou cliquer sur **Recruter**.
4. Après confirmation, le serveur inscrit la recrue. Le salon affiche le résultat après lecture de l’effectif natif. Le joueur peut sélectionner la recrue dans une composition du Club et la faire jouer dans un vrai match.

## Conversation et validation

- Réutiliser le service de chat et la sélection du moteur du salon. Ajouter un rôle de recrutement avec un brouillon structuré et versionné par session. Séparer le texte de l’agent des données de la fiche.
- Valider côté serveur le nom dans l’encodage et la longueur acceptés par la ROM, le poste, le niveau, les bornes des stats et les identifiants de techniques et de visuels. Pour la première version, choisir les techniques, sprites et portraits dans les catalogues reconnus par le jeu.
- Réserver l’inscription au bouton **Recruter**. L’agent propose des modifications au brouillon. Le serveur vérifie à la confirmation sa version, la révision de la session, l’état hors match et la capacité de l’effectif. Une confirmation répétée renvoie le résultat de la première inscription pour cette version.

## Intégration au jeu

1. Sur une copie de test de la ROM française BEBF, cartographier les références à `unitbase.dat` et `unitno.dat`. Vérifier la capacité des tables, les limites d’identifiant et les liens vers les noms, visuels et données de jeu. Ajouter une fiche de test avec un identifiant natif libre, puis vérifier que le moteur la charge et préserve les joueurs d’origine. Si nécessaire, étudier l’extension des tables ou l’usage d’une entrée réservée après avoir vérifié qu’elle est inutilisée. Un remplacement de joueur existant reste hors périmètre.
2. Valider le chemin d’inscription natif en prenant `src/scene_team.py` comme référence. Ce code initialise l’équipe au démarrage, tandis que le recrutement doit ajouter la recrue à une partie déjà ouverte. Vérifier aussi comment rendre la fiche disponible au moteur lors d’une reprise. Si un redémarrage ou une reconstruction de ROM est nécessaire, préserver et restaurer la progression du Club avant de proposer ce parcours dans le salon.
3. Vérifier l’inscription dans l’effectif et la sélection en match. Les amicaux actuels chargent des équipes invitées et restaurent le groupe d’exploration au retour. Ajouter une option **Mon équipe du Club** pour utiliser la recrue dans un match, puis vérifier qu’elle reste inscrite après le retour au local.
4. Conserver localement la fiche validée et son association à la partie Club. Vérifier l’identifiant dans l’état natif après sauvegarde et réouverture complète de melonDS. Prévoir une restauration de l’état précédent si une étape échoue, y compris après une écriture partielle. L’échec laisse le brouillon disponible pour réessayer.

## Critères de livraison

- Le joueur mène une conversation sur plusieurs tours et peut corriger ou annuler sa fiche. L’annulation laisse l’effectif intact.
- Une confirmation valide ajoute exactement une recrue. Une fiche invalide, un effectif plein, un match en cours ou une session devenue obsolète affiche un motif exploitable.
- Une recrue dotée d’un identifiant propre apparaît avec le nom attendu, peut être alignée et participe à un match natif. Les joueurs d’origine restent disponibles.
- La recrue reste dans l’effectif au retour au local et après fermeture, relance et chargement de la partie. Le test compare l’identifiant natif et les champs observables à la fiche confirmée.
- La suite existante et les smoke tests Club passent. Un essai dédié dans melonDS couvre la création, le match et la reprise. Documenter la révision et le hash de la ROM testée.

## Références du projet

- [Chargement des joueurs et effectif de départ](../TEAM_INITIALIZATION.md)
- [Parcours Club et retour de match](../CLUB_FRIENDLIES.md)
- [Chat, sessions et worker melonDS](../WEB_AND_MCP.md)
