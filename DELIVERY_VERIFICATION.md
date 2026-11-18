# Vérification de livraison — 18 novembre 2026

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
| Contrats et régressions | 47 tests unitaires passent ; compilation Python, syntaxe JavaScript et `git diff --check` passent. |
| Worker réel | Boot, capture PNG, révisions périmées, restauration du checkpoint et contrôle exclusif : `tests/smoke_session.py`. |
| Chat et organisateur réel | Demande « Fais s'affronter Occulte et Zeus », six répliques générées, arène prête : `build/browser/desktop-ready.png`. |
| Dialogue natif dynamique | Portrait de Talisman et texte généré visibles dans le jeu : `build/browser/desktop-dialogue.png`. |
| Affichage ordinateur/mobile | Captures à 1360×1000 et 390×844, aucun débordement horizontal ni erreur JavaScript : `build/browser/result.json`. |
| Effectif Occulte–Zeus | 16 unités domicile 41..56 et 16 unités adverses 181..196, lues dans la base native : `build/delivery/agent-final.json`. |
| Effectif Zeus–Occulte | Les deux ensembles inversés sont confirmés dans une nouvelle exécution : `build/delivery/reverse-rosters.json`. |
| Joueur visuel réel | 71 décisions/actions exécutées, passes, course et duels ; match à 17:43 de la première mi-temps : `build/delivery/agent-final.png`. |
| Arrêt et reprise | Annulation d'une décision Codex et retour au contrôle humain testés ; journal `build/delivery-smoke.log`. |
| Deux affiches dans le même worker | Réinitialisation du checkpoint puis Zeus–Occulte avec nouveau dialogue ; même session et même hash ROM : `build/delivery/second-fixture.json`. |
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

## Retour natif

L'essai de durée dans une session fraîche est suivi séparément dans
`build/native-session/`. Son résultat sera consigné ici à la fin de l'essai.
Une capture de jeu intermédiaire ne vaut pas acceptation du retour.
