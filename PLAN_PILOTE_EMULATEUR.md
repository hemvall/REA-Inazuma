# Plan du pilote de match sans modèle

Le bouton « L’agent joue pour moi » démarre une boucle déterministe. Elle lit l’émulateur, choisit une action proposée par le jeu et l’exécute. Le flux vidéo reste disponible pour le spectateur. Le pilote ne demande ni capture, ni appel à LM Studio ou Codex.

## Contrat avec l’émulateur

- `observe_match(session_id)` renvoie le numéro de frame, la révision, la phase, le score, le chrono, la possession, le joueur contrôlé et les actions légales. Un champ non validé reste inconnu.
- `apply_match_action(session_id, revision, frame, action_id)` vérifie le propriétaire de la session, la fraîcheur de l’observation et la légalité de l’action. Le worker applique l’action et renvoie le nouvel état.
- `advance_match(session_id, revision, frames)` avance au plus 120 frames sans entrée, pour les animations et chargements. Le worker s’arrête dès qu’un résultat natif est confirmé.
- `stop_agent(session_id)` interrompt la boucle. La commande en cours est bornée et aucune nouvelle action agent ne part après la reprise en main.

Les actions portent des identifiants sémantiques et, si nécessaire, une cible native. Exemples : `duel.dribble`, `pass.player.48`, `run.zone.left`, `shot.goal`. Le pilote ne manipule ni adresse mémoire ni coordonnées tactiles.

## Ordre d’implémentation

1. **Duels.** Repartir du checkpoint `field.state` et des captures du script `local/probe_duel_ram.py`. Identifier le champ natif qui distingue une décision de duel d’une simple position du stylet. Vérifier sa lecture sur plusieurs duels offensifs et défensifs. Identifier ensuite le mécanisme qui applique chaque choix et vérifier qu’une action directe produit le même effet qu’un choix manuel depuis le même état sauvegardé. `choose_duel` utilise encore le tactile et sert de référence de comparaison.
2. **Jeu libre.** Identifier le joueur contrôlé et les états qui autorisent une passe, une course, un tir ou une interception. Pour chaque action, valider le format de la commande et la cible sur des états reproductibles. Vérifier que le jeu change de possession, déplace le bon joueur ou déclenche le tir selon l’action. Exposer uniquement les commandes confirmées pour la ROM et le cœur compatibles.
3. **Transitions.** Exposer la préparation, la formation, l’engagement, le ralenti, la mi-temps et le résultat. Réutiliser les règles vérifiées pour les transitions, puis compléter la lecture native des phases manquantes. Une phase inconnue peut avancer sans entrée pendant un délai borné. Si elle persiste, rendre la main avec la phase et la frame dans le journal.
4. **Remplacement du pilote.** Brancher la boucle sur le bouton existant. Retirer de ce parcours l’appel au modèle et les clics cycliques sur écran inconnu. Conserver le journal des observations, actions acceptées, rejets et délais pour diagnostiquer les blocages.

## Règles de décision

Sur un menu, prendre l’action de progression proposée. En duel, choisir l’option légale selon une priorité fixe et stable. Avec le ballon, tirer si le tir est disponible, sinon passer vers un partenaire mieux placé, sinon avancer. Sans le ballon, tenter une interception légale ou revenir défendre. Sans action légale, avancer l’animation par petits lots, puis relire l’état.

Si une commande est périmée, relire l’état. Si la même action échoue trois fois ou que la phase et le chrono restent figés malgré les tentatives, rendre la main et conserver la trace. Les règles n’inventent jamais une action absente de la liste.

## Validation

- Sur checkpoint, refuser un choix illégal, une révision périmée et une action demandée après reprise en main. Vérifier chaque commande par son effet observé dans le jeu.
- Depuis le navigateur, jouer intégralement Occulte–Zeus puis Zeus–Occulte jusqu’au résultat confirmé par l’émulateur, avec LM Studio arrêté. Vérifier le direct et « Reprendre la main » pendant une rencontre séparée.
- Mesurer les écarts entre actions de jeu acceptées. Exiger moins de 10 secondes entre actions lorsque le jeu attend une entrée. Journaliser séparément les animations imposées. Les avances sans entrée ne comptent pas comme actions utiles.
- Conserver pour chaque essai le résultat natif, le plus grand écart mesuré, le nombre de commandes rejetées et les compteurs d’appels texte et vision à zéro.
