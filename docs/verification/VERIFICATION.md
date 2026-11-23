# Vérifications

Exécuter les commandes depuis la racine du dépôt avec Python 3.11 ou supérieur.

## Tests unitaires

```powershell
python -m pip install -r requirements-ai.txt -r requirements-rom.txt
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
```

Audit du 23 novembre 2026 sur la base `31ff76a` (Python 3.12) : 121 tests
recensés, 119 réussis et 2 ignorés. Les deux tests ignorés nécessitent des
captures locales du cœur ou une trace native de but. Les tests couvrent
notamment les contrats de session, le choix d’action, le recrutement et les
bilans de Chester.

## Essais d’intégration

Les essais natifs nécessitent la ROM et le cœur exacts du [guide de livraison](../guides/DELIVERY.md#prérequis).
Les scénarios lancés par les scripts ci-dessous disposent de leur propre worker.

| Commande | Contrôle |
| --- | --- |
| `python tests/smoke_emulator_pilot.py` | Pilote déterministe sur les deux sens d’Occulte–Zeus, commandes périmées et reprise en main. Le script relève les arrêts sur écran inconnu et peut passer sans atteindre le résultat. |
| `python tests/smoke_emulator_pilot.py --duel-checkpoint` | Contrat des actions en duel, dont l’accès aux supertechniques quand le menu est reconnu. |
| `python tests/smoke_club.py` | Parcours et effectifs des matchs amicaux du Club. |
| `python tests/smoke_native_club.py` | Lancement des deux rencontres de la route native et restauration du groupe après annulation. |
| `python tests/smoke_recruitment_rom.py` | Persistance du recrutement natif et présence de la recrue dans le jeu. Ajouter `--lobby` pour vérifier la confirmation depuis le salon, les deux côtés de l’arène et l’import dans le local. |
| `python tests/smoke_session.py` | Worker et checkpoints sur le profil historique. Construire d’abord la ROM du [Défi Mystère](../guides/RUN_SCENARIO.md#rebuild). |

Avec le serveur web ouvert, `local/agent-venv/Scripts/python.exe tests/smoke_mcp.py`
vérifie la connexion MCP. Ajouter `--read-only` pour éviter de prendre la main
sur la session. `python tests/smoke_delivery.py` agit sur la session ouverte
et appelle le coach local si aucune rencontre n’est prête. Il utilise le pilote
déterministe et peut interrompre une partie en cours. Ajouter `--require-result` pour exiger un résultat natif.

### Résultats natifs de l’audit du 23 novembre 2026

| Rencontre | Résultat observé | Actions | Plus grand écart entre actions |
| --- | --- | ---: | ---: |
| Occulte–Zeus | Arrêt en jeu libre sur un écran inconnu, frame 29 477 | 71 | 11,91 s |
| Zeus–Occulte | Fin native confirmée, 1–1, frame 40 198 | 90 | 12,66 s |

Les deux essais ont utilisé le pilote déterministe, avec zéro appel texte ou
vision et zéro commande rejetée pendant le pilotage. La reprise en main a
bien révoqué les commandes du pilote. Les captures sont dans
`build/pilot-smoke/`.

Les essais du Club ont validé ses affiches, la restauration du groupe et
l’annulation. Le profil natif a lancé les deux rencontres attendues. Les
essais de recrutement ont confirmé la persistance après réouverture et
l’arrivée d’une recrue de niveau 30. Depuis le salon, la recrue a été
observée à domicile, à l’extérieur et dans le local.

Le Défi Mystère a été reconstruit dans un dossier temporaire. Le contrôle
structurel a validé 24 entrées de script et de texte. Le worker a démarré
et validé la capture PNG, les révisions et la restauration du checkpoint.
L’essai s’arrête après le démarrage.

Le test MCP en lecture seule a validé la découverte des outils, les
capacités, le statut et le catalogue natif sur un serveur isolé.

Les essais de cet audit n’ont pas rejoué le parcours complet du coach et du
pilote IA avec LM Studio, ni la synthèse vocale dans un navigateur. Les
rapports ci-dessous datent les validations précédentes.

## Rapports datés

- [Livraison web et MCP du 18 novembre 2026](DELIVERY_VERIFICATION.md)
- [Scénario historique et limites observées](RUNTIME_VERIFICATION.md)
- [Procédure d’acceptation du scénario](../../tests/smoke_tests.md)

Les rapports structurels historiques sont produits dans
`build/verification.json` et `build/scene_semantics.json`. Les captures,
sauvegardes, ROM et journaux restent locaux.
