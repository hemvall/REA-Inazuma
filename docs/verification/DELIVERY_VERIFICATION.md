# Vérification de livraison — 18 novembre 2026

> Document historique. Voir le [index des vérifications actuelles](VERIFICATION.md).

## Identités testées

- Original BEBF révision 0 :
  `1e67c699a6b3ecfb5230e8c2245746879fab57123277651da74b4cc9b8ba25d3`.
- Arène : `46b1631976b4a065012e4136063b3546dd7e2fe8f2c5464c2a4661c7dc91731c`.
- melonDS Libretro 0.9.3 4081e83, DLL :
  `e50e675eab350e14d1cb9ccc4ada7f09fb6a3e6dcd16ef4a197d9a5b8a656f13`.
- Python 3.12 ; SDK MCP 1.30.0 ; navigateur Edge via Playwright.

## Essais acceptés

| Essai | Preuve |
|---|---|
| Construction et réversibilité exacte | `build/arena/verification.json` : manifeste exact, 223946 octets modifiés, inversion vérifiée. |
| Contrats et régressions | 54 tests unitaires passent ; compilation Python, syntaxe JavaScript et `git diff --check` passent. |
| Worker réel | Boot, capture PNG, révisions périmées, restauration du checkpoint et contrôle exclusif : `tests/smoke_session.py`. |
| Chat et organisateur réel | Demande « Fais s'affronter Occulte et Zeus », six répliques générées, arène prête : `build/browser/desktop-ready.png`. |
| Dialogue natif dynamique | Portrait de Talisman et texte généré visibles dans le jeu : `build/browser/desktop-dialogue.png`. |
| Affichage ordinateur/mobile | Captures à 1360×1000 et 390×844, aucun débordement horizontal ni erreur JavaScript : `build/browser/desktop-final.png`, `build/browser/mobile-final.png`, `build/browser/result.json`. |
| Effectif Occulte–Zeus | 16 unités domicile 41..56 et 16 unités adverses 181..196, lues dans la base native : `build/delivery/agent-final.json`. |
| Effectif Zeus–Occulte | Les deux ensembles inversés sont confirmés dans une nouvelle exécution : `build/delivery/reverse-rosters.json`. |
| Joueur visuel réel | 71 décisions/actions exécutées, passes, course et duels ; match à 17:43 de la première mi-temps : `build/delivery/agent-final.png`. |
| Arrêt et reprise | Annulation d'une décision Codex et retour au contrôle humain testés ; journal `build/delivery-smoke.log`. |
| Deux affiches dans le même worker | Réinitialisation du checkpoint puis Zeus–Occulte avec nouveau dialogue ; même session et même hash ROM : `build/delivery/second-fixture.json`. |
| Match complet et retour protégé | Le service HTTP atteint `phase=result`, `result_source=native_final_screen`, puis B restaure le salon sans arrêter le worker : `build/live-lifecycle/final.json`, `final.png`. |
| Rejeu après résultat | Zeus–Occulte et nouveau dialogue d'Aphrodite dans la même session `7d1c959df6c54e19bc775a4893a2c21b`, même hash ROM et cœur : `build/live-lifecycle/return-and-replay.json`, `return-and-replay.png`. |
| MCP réel | Initialisation, découverte complète, catalogue, état, commande DS, contenu image et fermeture : `tests/smoke_mcp.py`, avec et sans `--read-only`. |

Les images, ROM, états et journaux cités sont des preuves privées locales,
conservées hors Git et hors du ZIP source.

## Portée de l'agent joueur

Le joueur visuel est fonctionnel et a effectivement piloté le match. Son essai
borné à 80 itérations a atteint sa limite à 17:43 ; il ne constitue pas une
preuve de victoire ou de fin de match. La livraison utilise par défaut un budget
de 400 itérations, annulable à tout moment. Les décisions peuvent être lentes
et leur qualité tactique reste expérimentale. L'émulation reste en pause
pendant la réflexion ; un budget épuisé ne fabrique pas de résultat.

## Fin et retour au salon

Un match natif complet a atteint « Fin du match » à 0–9 avec le contrôleur de
régression, distinct de l'agent Codex : `build/delivery/native-final-score.png`.
Le retour natif par B a ensuite fait arrêter le cœur. Ce défaut n'est pas
présenté comme un retour accepté.

La correction reconnaît le titre natif par une signature de pixels mesurée,
y compris dans un écran assombri, suspend immédiatement les entrées et conserve
la capture finale. Le retour utilisateur restaure le checkpoint initial au lieu
d'appeler le retour natif défectueux. Des tests vérifient l'arrêt sans frames
de relâchement supplémentaires et la distinction avec la mi-temps.

L'essai final passe par le service HTTP livré, ses révisions et ses commandes
bornées. Il a atteint l'écran final à la frame 120008, révision 1363, avec les
deux effectifs natifs confirmés. La capture est volontairement figée dès la
première reconnaissance du titre, pendant son apparition, et reste assombrie.

La commande B suivante restaure le compteur 4 et enlève l'affiche ; l'identifiant
de session reste identique. La préparation inversée et son lancement atteignent
ensuite le compteur 2 avec Aphrodite et « Zeus accueille Occulte. », révision
1371. Le journal `build/live-lifecycle.log` termine par
`PASS FULL NATIVE RESULT, SAFE B RETURN, SAME SESSION AND REVERSE DYNAMIC FIXTURE`.

Ce test de durée utilise un contrôleur de régression et onze décisions Codex
pour les écrans nécessitant une reprise visuelle. Il prouve le cycle natif et
le retour du système livré ; il ne constitue pas une preuve de victoire du
joueur Codex seul. Le retour brut de la ROM demeure remplacé par le contrôleur.
