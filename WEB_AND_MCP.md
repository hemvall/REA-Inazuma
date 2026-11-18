# Salon web et MCP

## Démarrage local

Double-cliquer `Lancer InazumIA.cmd`. Le lanceur construit ou vérifie la ROM
d'arène, démarre le serveur sur `127.0.0.1:8765` et ouvre le navigateur.
La première ouverture initialise une nouvelle partie dans melonDS ; cette
préparation peut prendre environ une minute. Sa progression reste visible dans
le salon. Les commandes suivantes partagent ce même processus d'émulation.

Le chat appelle un agent organisateur avec le moteur sélectionné. Il résout les deux équipes et écrit
six répliques originales, alternant les capitaines. La préparation manuelle
propose un dialogue court prédéfini si l'on ne souhaite pas appeler cet agent.
Le catalogue de cette livraison contient Occulte et Zeus, dans les deux sens.

« Lancer le dialogue » ouvre l'échange dans le jeu. « Continuer » fait avancer
le temps ; « Pause » l'arrête. Le clavier, les boutons DS et les clics/glissers
sur l'écran inférieur commandent le même worker. Les coordonnées DS vont de
0 à 255 en x et de 0 à 191 en y, exclusivement sur l'écran inférieur.

Le salon de bureau utilise une échelle de 125 % à partir de 1000 pixels de
largeur ; conserver le zoom du navigateur à 100 % pour cette taille. Les deux
écrans sont intégrés dans une DS blanche dessinée en CSS pixel art. Les éléments
de sa coque sont décoratifs ; les commandes restent disponibles dans « À la
manette », au clavier et sur l'écran tactile inférieur.

La lecture humaine envoie deux frames DS par requête, avec une cible de
30 affichages par seconde (60 frames DS/s). Les requêtes sont séquentielles :
une machine lente ne cumule pas de commandes. Le suivi du statut reprend en
pause ; pendant la lecture, les réponses des commandes actualisent l'écran.

« L'agent joue pour moi » appelle un agent visuel avec ce même moteur. Il observe les
deux écrans et choisit les entrées DS. Le cœur attend pendant chaque décision.
« Reprendre la main » annule la décision en cours et rend le contrôle humain.
Chaque action est bornée ; une attente d'animation peut regrouper quatre segments
de 120 frames. Quatre frames de relâchement séparent les appuis et les glissers
pour que le jeu échantillonne le relâchement même pendant ses mises à jour à 30 Hz.
Un segment peut s'arrêter avant sa limite lorsque le résultat final est détecté ;
la frame reste alors figée jusqu'au retour au salon.

« Nouvelle rencontre » restaure le checkpoint initial du worker : la ROM n'est
ni reconstruite ni rechargée. Une nouvelle affiche et de nouveaux dialogues
peuvent alors être injectés. Les checkpoints utilisateur restent éphémères et
appartiennent exclusivement à la session courante.

À l'écran natif « Fin du match », le contrôleur conserve le résultat et suspend
le cœur. « Nouvelle rencontre », B ou un clic de continuation rétablit le salon
depuis le checkpoint de cette même session. Ce retour est géré par le worker :
le retour natif direct de cette arène a provoqué un crash pendant les essais et
n'est pas utilisé. La ROM d'arène doit donc être jouée avec ce contrôleur, et
non comme une ROM autonome dans un autre frontend.

## Agents et connexion

Le sélecteur « Moteur des agents » propose **IA locale · LM Studio** et
**Codex CLI · compte connecté**. Le choix est enregistré dans
`build/agents/settings.json` et ne peut pas changer pendant une opération.
L'IA locale est sélectionnée lors du premier lancement. La variable
`INAZUMIA_AGENT_BACKEND` (`local` ou `codex`) peut imposer le moteur au démarrage.

### IA locale

Démarrer le serveur local dans LM Studio, sur le port 1234, avec le modèle
visuel `qwen/qwen3.5-9b` déjà disponible sur ce PC. Aucun compte ni clé API
n'est requis. Les demandes et captures sont envoyées uniquement au serveur
HTTP de la machine, sans appel à Codex CLI.

Les variables `INAZUMIA_LLM_URL` (défaut `http://127.0.0.1:1234/v1`) et
`INAZUMIA_LLM_MODEL` permettent de choisir un autre serveur compatible ou modèle.
Seules les adresses de boucle locale sont acceptées. Le joueur exige un modèle
visuel ; les deux agents exigent des réponses JSON structurées. Le délai maximal
est de 180 secondes par décision. Annuler rend immédiatement le contrôle ;
l'inférence déjà envoyée peut continuer sur le serveur, mais sa réponse est ignorée.
Les requêtes locales utilisent `reasoning_effort: "none"` pour éviter que Qwen
consomme le budget dans son raisonnement interne. Le salon affiche le temps
d'attente de la décision ; le jeu reste en pause pendant celle-ci. La vitesse
et la qualité des actions dépendent toujours du modèle et du matériel.

### Codex CLI

Ce choix conserve le CLI Codex déjà installé et l'authentification existante.
Vérifier `codex login status` ; si nécessaire, se connecter avec `codex login`.
Chaque décision est une exécution éphémère en lecture seule, sans chargement de
la configuration utilisateur du CLI. Les agents n'ont pas besoin d'une clé API.
Ils consomment l'usage associé à votre compte Codex. Le modèle doit accepter
les images et les réponses structurées. Un échec, un délai dépassé ou un budget
épuisé laisse le jeu en pause et fournit une erreur explicite dans le salon.

Les prompts, sorties et journaux restent dans `build/agents/`. Les sessions
gardent leurs commandes dans `build/sessions/<id>/replay.jsonl`, leurs images
et le journal natif `native.log`. Ces fichiers restent hors Git et du ZIP source.

## Installer et configurer MCP

Exécuter `Installer MCP.cmd`, ou :

```powershell
python -m venv local/agent-venv
local/agent-venv/Scripts/python.exe -m pip install -r requirements-agent.txt
```

Le SDK officiel est fixé à `mcp==1.30.0`, API v1 :
https://py.sdk.modelcontextprotocol.io/v1/.

L'installateur génère aussi `build/mcp-client.json` et `build/mcp-codex.toml`,
avec les chemins absolus de votre installation. Importer le premier dans un
client compatible, ou ajouter le contenu du second à la configuration Codex.
`python src/configure_mcp.py` régénère ces fichiers si le dossier a été déplacé.

Configurer votre client MCP avec l'exécutable absolu
`<projet>/local/agent-venv/Scripts/python.exe` et l'argument absolu
`<projet>/src/mcp_server.py`. Exemple Codex TOML, en remplaçant les chemins :

```toml
[mcp_servers.inazumia]
command = 'C:\chemin\InazumIA\local\agent-venv\Scripts\python.exe'
args = ['C:\chemin\InazumIA\src\mcp_server.py']
```

Le serveur web doit être ouvert. L'adaptateur MCP est un client du même service
local : il ne crée pas une seconde émulation et son stdout reste réservé à MCP.

Outils : `capabilities`, `list_teams`, `organise_match`, `prepare_match`,
`get_match_status`, `session_open`, `observe`, `start_match`, `step`, `touch_path`,
`checkpoint_save`, `checkpoint_load`, `reset_match`, `delegate_player`,
`stop_player`, `session_close`.

La préparation et les agents renvoient un job ; consulter `get_match_status`
jusqu'à son état terminal. `observe` renvoie une image MCP réelle des deux écrans
et la révision. Une mutation exige cette révision. Avant les commandes directes
du client externe, cliquer « Autoriser le client MCP » dans le salon. L'agent
joueur intégré possède son propre transfert de contrôle.

## Vérification

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python tests/smoke_session.py
local/agent-venv/Scripts/python.exe tests/smoke_mcp.py
python tests/smoke_delivery.py
```

Les deux derniers tests utilisent le service ouvert et modifient sa session.
`smoke_delivery.py` appelle les vrais agents, puis prépare l'affiche inversée
dans le même worker. Il conserve des captures et des identités dans
`build/delivery/`. Une suite de tests verts n'est pas une garantie que le joueur
visuel gagnera un match ; ses décisions et son niveau de jeu restent observables.

Pour exiger aussi un résultat final dans l'essai du joueur visuel, avec un budget
plus long et une durée maximale explicite :

```powershell
python tests/smoke_delivery.py --max-decisions 400 --require-result --timeout 7200
```

Ce mode échoue si l'agent s'arrête avant le résultat ; il ne transforme pas une
limite de budget en réussite de match.
