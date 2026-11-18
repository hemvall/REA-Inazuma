# Chat, rencontres dynamiques et agent joueur

## Suivi de livraison du 18 novembre 2026

- [x] Branche `develop` dans le dépôt réel `REA-Inazuma`.
- [x] Front web avec chat, deux écrans, commandes DS et glissers tactiles.
- [x] Coque ROM fixe et préparation dynamique des équipes et des dialogues en RAM.
- [x] Occulte et Zeus, dans les deux sens, avec effectifs et capitaines vérifiés.
- [x] MCP partagé avec le navigateur : préparation, lancement, observation,
  entrées, checkpoints, réinitialisation et délégation.
- [x] Agent organisateur Codex et joueur visuel Codex distinct, appelé sur demande.
- [x] Annulation, contrôle exclusif et reprise manuelle.
- [x] Deux affiches préparées dans le même worker sans reconstruction/rechargement.
- [x] Lanceur local, documentation et constructeur de ZIP source.
- [ ] Consigner la fin et le retour du test natif de durée en cours.

Le rapport courant est `DELIVERY_VERIFICATION.md`. Les sections suivantes
conservent le plan initial et les étapes de recherche ; leurs descriptions de
blocages historiques ne remplacent pas ce suivi de livraison.

## Objectif

Depuis un chat web, demander une rencontre telle qu’Occulte contre Zeus, voir
un bref dialogue entre les capitaines puis jouer ou déléguer à un agent.
Les rencontres suivantes doivent être chargées dans la même session sans
reconstruction ni rechargement de la ROM.

## État et ordre d'exécution

- [x] Créer la branche develop et enregistrer le plan.
- [ ] Valider le scénario actuel jusqu'au résultat, retour et rejeu sous melonDS.
- [ ] Extraire un worker isolé : IPC indépendant de stdout natif, pause, frames,
  capture, maintien tactile, fermeture, timeout et checkpoints liés aux hashes.
- [ ] Mesurer le chargement natif des équipes et des matchs sur BEBF révision 0.
  Valider Occulte et Zeus, leurs capitaines et les formats effectivement disponibles.
- [ ] Réserver une zone RAM avec durée de vie prouvée et installer une seule fois
  un pont ROM. Préserver overlays, registres, cache et retour du code natif.
- [ ] Implémenter le protocole dynamique : version, request_id, longueur,
  configuration, validation ROM, acquittement, erreur et délai maximal.
  États : idle, preparing, ready, dialogue, playing, result, error.
- [ ] Charger équipes, compositions et ressources par leurs routines natives,
  puis quatre à six répliques validées et le lancement du match.
  Refuser les changements pendant le jeu et les identifiants inconnus.
- [ ] Exposer le MCP local : list_teams, prepare_match, get_match_status,
  start_match, observe, step, touch_path, checkpoint_save/load, session_close.
  Un seul contrôleur par session ; toute action vérifie sa révision.
- [ ] Construire le front local : chat, fiche de rencontre, deux écrans DS,
  clavier/tactile, pause, délégation et reprise de contrôle dans le même worker.
- [ ] Ajouter l'organisateur : résolution des noms, dialogues structurés,
  outils autorisés et restitution des erreurs réelles.
- [ ] Ajouter l'agent joueur optionnel : observation validée, actions DS bornées,
  pause pendant les décisions, interruption et journal rejouable.
- [ ] Valider deux affiches/dialogues successifs sans recharger la ROM, puis
  délégation, reprise manuelle, résultat et rejeu dans le navigateur.

## Contraintes et preuves

Le défi actuel à quatre joueurs au premier but ne prouve pas le lancement d'un
match complet à onze. Aucun offset, capitaine ou identifiant ne doit être inventé.
Le MCP reste sur le PC. Une écriture RAM seule ne constitue pas un chargement natif.
La zone RAM et les hooks restent à découvrir : aucune capacité dynamique ne doit
être annoncée disponible avant acquittement et vérification visuelle en exécution.
ROM, ressources extraites, sauvegardes et checkpoints restent hors Git.

## Vérification

Tests de contrats : tailles, version, requêtes répétées, révisions périmées,
contrôle exclusif, phase incorrecte, délais et restauration incompatible.
Tests réels : identité ROM/cœur, captures des dialogues, équipes effectivement
chargées, actions tactiles continues, résultat, retour, deuxième rencontre.
Chaque lot conserve ses commandes, résultats et limitations ; les tests simulés
ne remplacent jamais les preuves d'exécution du pont ROM.

## Avancement du 17 novembre 2026

Implémenté : worker melonDS isolé et IPC Pipe, segments bornés, observation PNG,
révisions, fermeture et délais, checkpoints éphémères limités à huit, verrou de
session et transfert humain/agent externe. Service HTTP local et adaptateur MCP
partagent la même session. Front HTML/CSS/JS avec chat à règles, affichage DS,
commandes, pause et transfert de contrôle. Contrat binaire proposé pour le pont
dynamique : version, taille, CRC, request_id, états et acquittement.

Vérifié : 42 tests unitaires, boot réel melonDS, capture, rejet de révision périmée,
restauration du checkpoint, contrôle exclusif ; handshake MCP, découverte des
outils, commande et image via le service HTTP. Page web : HTTP 200 et JavaScript
valide syntaxiquement. Le rendu et les interactions navigateur ne sont pas
validés visuellement : l'outil navigateur échoue à initialiser ses fichiers.

Empreintes du test : ROM
`7a9435be30fea323a5d445d9f91355dd89f9e0bce714ca96954cc0f64d865033`,
cœur `e50e675eab350e14d1cb9ccc4ada7f09fb6a3e6dcd16ef4a197d9a5b8a656f13`.
Ce build présent sur disque diffère du dernier build décrit dans
RUNTIME_VERIFICATION.md ; les anciennes preuves ne sont pas transférées.

Restant : observation sémantique, hooks et allocation RAM, chargement natif des
équipes/dialogues, agent organisateur LLM et joueur autonome, résultats/rejeu,
journal complet, sauvegarde durable et validation navigateur. Le parseur du chat
et l'autorisation d'un client MCP ne constituent pas ces agents.

Limitation REA constatée : le CLI 6.9.0 refuse Node 26.12.0, exigeant au minimum
26.12.1 dans cette branche. Aucun runtime système n'a été remplacé. Cette limite
ne prouve pas que le pont dynamique est impossible ; sa recherche reste ouverte.

Mode d'emploi et commandes : [WEB_AND_MCP.md](WEB_AND_MCP.md).

## Reprise du 18 novembre 2026

La construction expérimentale `prepare_arena.py` et le pont `arena_bridge.py`
restent déconnectés du service public. La préparation des données en RAM est
possible, mais changer le compteur natif ne redéclenche pas le callback 0x1017.
Deux essais de réinsertion dans la file native (callback puis clé d'événement)
ne déclenchent pas le dialogue. `start()` refuse désormais explicitement ce
chemin, au lieu de retourner un faux état de démarrage.

Prochaine investigation : comprendre l'ordonnancement des threads SSD
(contexte 0x020D9848, stride 0x22C) et les préconditions de 0x020606B4 avant
d'intégrer le pont. Les expériences privées et leurs captures sont conservées
dans `local/` et `build/research/`, hors Git. Le lancement Occulte–Zeus,
le retour, le deuxième match et le joueur autonome ne sont pas acceptés.

### Scène d'attente native

Le callback démarre désormais normalement et affiche une invitation à préparer
la rencontre. Son compteur 4 identifie cette attente. Le pont prépare les buffers
existants puis envoie A par les entrées DS. Le test `local/test_arena.py` confirme
le passage du compteur 4 à 2 et la capture `build/research/arena-dialogue.png`
montre Talisman avec la première réplique Occulte–Zeus injectée à chaud.
ROM expérimentale :
`718d93b68874e3df3245d0c4d606fec1ad8c6fb1b90b630641a92bc909fb9d76`.
Cette preuve remplace le refus de start pour cette nouvelle ROM uniquement ;
elle ne prouve pas encore le lancement du match ou le retour.

La même exécution atteint ensuite le compteur 10 et l'écran natif « Sortez
votre stylet ! » (`build/research/arena-play-12.png`). Cela confirme la transition
vers le lancement football, sans prouver encore les effectifs sur le terrain,
le coup d'envoi, le résultat ou le rejeu.
