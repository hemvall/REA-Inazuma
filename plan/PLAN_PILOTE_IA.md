# Plan d’ajout d’un agent IA au pilote de match

## Objectif

Donner au pilote la capacité de choisir entre plusieurs actions légales à partir des informations que l’émulateur fournit déjà. La première version traite les choix exposés par `legal_actions`, notamment les duels. L’exposition de nouvelles actions de passe, de course ou de tir relève du [plan du pilote émulateur](../PLAN_PILOTE_EMULATEUR.md).

## Contrat de décision

- **Entrée.** L’agent reçoit l’observation structurée de `observe_match`, avec la phase, l’écran reconnu, le score, le chrono, la possession, le joueur contrôlé et la liste des actions légales. Les valeurs inconnues restent telles quelles. L’appel au modèle se fait en texte, sans capture.
- **Sortie.** L’agent renvoie un seul identifiant proposé par l’émulateur, par exemple `{"action_id":"duel.feint"}`. Le schéma JSON impose `action_id` et limite ses valeurs à celles de `legal_actions`. Le pilote vérifie aussi le format et l’appartenance de l’identifiant à cette liste.
- **Exécution.** Le pilote appelle `apply_match_action(session_id, revision, frame, action_id)` avec la frame et la révision de l’observation qui a servi à la décision. Le worker vérifie la fraîcheur de l’observation et la légalité de l’action. La session vérifie qui détient le contrôle.

## Étapes d’implémentation

1. **Brancher la décision dans `Arena.delegate`.** Dans [src/arena_service.py](../src/arena_service.py), remplacer la sélection systématique du premier identifiant par un choix selon le mode actif. En mode IA, appeler le modèle seulement lorsque plusieurs actions légales sont disponibles. Avec une seule action, l’exécuter directement. Sans action disponible, conserver l’avance bornée via `advance_match` et la détection de blocage. Conserver les temporisations, l’arrêt sur résultat natif et le retour de contrôle.
2. **Ajouter une méthode de décision au backend actuel.** Dans [src/agent_runtime.py](../src/agent_runtime.py), réutiliser la génération structurée et l’annulation existantes. Construire le schéma à partir de `legal_actions` à chaque décision. Garder la boucle sémantique comme point d’intégration du nouveau mode.
3. **Gérer les échecs et les réponses tardives.** Sur réponse invalide, délai dépassé ou modèle indisponible, reprendre le premier choix légal si la session est toujours sous contrôle du pilote. Sur observation périmée, relire l’état et recalculer la décision. Vérifier l’annulation avant tout envoi et écarter les réponses arrivées après « Reprendre la main ». Conserver les vérifications du [worker et de la session](../src/game_session.py).
4. **Exposer le mode IA dans l’interface.** Mettre à jour le parcours « L’agent joue pour moi » dans [web/app.js](../web/app.js) et transmettre le mode choisi au lancement du pilote. Garder le mode déterministe par défaut lors du premier déploiement. Journaliser le mode effectif, l’action retenue, le temps de décision et le motif d’un éventuel retour au choix déterministe.

## Supertechniques en duel et lors d’un arrêt

Le pilote choisit parmi les actions exposées par `legal_actions`. Aujourd’hui, [`match_actions.py`](../src/match_actions.py) expose deux actions ordinaires par écran de duel, dont `keeper.punch` et `keeper.catch` pour le gardien. L’action `shot.block_special` correspond à un écran distinct. Elle ne donne pas accès au choix d’une supertechnique depuis les duels.

1. **Relever le parcours natif dans melonDS.** Capturer un checkpoint pour chaque cas : duel offensif, duel défensif et arrêt du gardien. Relever les entrées et signatures du menu de supertechniques, des choix disponibles, des choix grisés et du retour. Vérifier les variations selon le joueur, les techniques apprises et les PT restants.
2. **Exposer les actions légales.** Étendre [`frame_state.py`](../src/frame_state.py) et [`match_actions.py`](../src/match_actions.py) pour reconnaître l’accès au menu lorsqu’il est utilisable et exposer chaque technique sélectionnable. Si le jeu ouvre un sous-menu, publier une nouvelle observation à son ouverture. Fournir des identifiants stables et les données vérifiées qui aident le pilote à choisir, comme le nom et le coût en PT. Réutiliser les contrôles de frame, de révision et de légalité pour chaque entrée.
3. **Faire choisir le pilote.** Donner au modèle le choix entre action ordinaire et supertechnique autorisée. Lui fournir le score, le chrono et les données vérifiées sur le joueur et la menace. Favoriser les supertechniques quand le gain tactique justifie les PT, notamment face à un tir dangereux. Garder un choix ordinaire légal en repli sur le duel et prévoir un retour légal si le sous-menu est déjà ouvert.
4. **Vérifier en jeu.** Depuis les trois checkpoints, forcer un choix de supertechnique puis vérifier que le jeu joue la technique attendue et décompte les PT lorsque la règle native le prévoit. Couvrir aussi un choix ordinaire malgré une technique disponible, des PT insuffisants, une technique grisée, un écran inconnu, une observation périmée et la reprise en main pendant la sélection. En match complet, relever les techniques effectivement jouées et les replis pour vérifier le comportement du pilote sans choix forcé.

## Validation

- **Choix réel.** Depuis un checkpoint de duel avec deux options, faire renvoyer la deuxième par le modèle. Vérifier que le worker exécute cet identifiant et que l’effet attendu apparaît dans l’état du jeu.
- **Réponses invalides.** Tester un identifiant interdit, un format invalide, un modèle indisponible et un dépassement du délai. Vérifier que seule une action légale peut être exécutée.
- **Fraîcheur et reprise en main.** Tester une frame ou une révision périmée et une reprise en main pendant l’appel au modèle. Vérifier la relecture après rejet et l’absence de commande agent après le transfert de contrôle.
- **Régression.** Vérifier que le mode déterministe fonctionne avec le modèle arrêté. En mode IA, vérifier que les choix uniques et les transitions sans action déclenchent zéro appel modèle. Réutiliser [tests/smoke_emulator_pilot.py](../tests/smoke_emulator_pilot.py) pour les vérifications natives.
- **Matchs complets.** Jouer Occulte–Zeus puis Zeus–Occulte jusqu’au résultat confirmé par l’émulateur. Mesurer l’écart entre actions acceptées quand le jeu attend une entrée, avec l’objectif existant de moins de 10 secondes. Compter les appels texte, les retours au choix déterministe et les commandes rejetées. Comptabiliser à part les animations imposées et vérifier que le compteur d’appels vision reste à zéro.
