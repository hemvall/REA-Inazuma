# InazumIA — notes de soutenance

## 1. Introduction · 0:00–0:20 · A

- « InazumIA est un salon web pour organiser et jouer des rencontres de football dans Inazuma Eleven 2 sur Nintendo DS. »
- « On va suivre une seule rencontre, Occulte contre Zeus, de la consigne écrite jusqu’à une action dans le match. »

## 2. Plan · 0:20–0:30 · A

- « On présente l’application et ses agents, puis on passe à la démo et au bilan. »

## 3. L’application · A

- [Passer à la capture du salon.]

## 4. Le salon · 0:30–1:00 · A

- [Montrer la capture.] « On prépare l’affiche dans le salon, on joue sur les deux écrans de la DS et on suit le commentaire. »
- « Le joueur peut garder le clavier et le tactile, ou déléguer le match. Il peut reprendre la main pendant la partie. »

## 5. Architecture applicative · 1:00–1:45 · A

- « Le frontend est en HTML, CSS et JavaScript. Il envoie des requêtes JSON à un serveur Python local. »
- « Le serveur gère la session. Un worker isolé exécute la ROM dans melonDS Libretro et applique les entrées DS. »
- « Le navigateur reçoit l’état de la session et le flux vidéo des deux écrans. Le résultat que vous voyez est produit par le jeu. »
- [Passer la parole.] « La même API relie ces commandes aux trois agents. »

## 6. Les agents IA · B

- [Enchaîner sur le coach.]

## 7. Coach IA · Préparer le match · 1:45–2:45 · B

- « Le backend déclenche chaque agent au moment où sa responsabilité intervient. »
- « Le coach reçoit la consigne et le catalogue. Il propose deux identifiants d’équipe et six répliques. Le backend vérifie ces valeurs puis prépare la rencontre dans la session. »
- « La rencontre préparée par le coach est celle que le pilote va jouer et que Chester va commenter. Les trois rôles partagent la même session. »
- « LangChain lance le modèle dans LM Studio et valide les réponses structurées par schéma JSON. Les vérifications métier se font ensuite dans le backend. »

## 8. Pilote IA · Jouer à la place du joueur · 2:45–3:25 · B

- [Montrer les deux écrans de duel.] « Le worker reconnaît certains menus et produit une liste d’actions légales. En mode IA, quand plusieurs options sont disponibles, le modèle peut choisir un identifiant. »
- « Le backend envoie cet identifiant au worker. Il vérifie la session, la révision, la frame et la légalité, puis applique l’entrée tactile DS. »
- « Le délai est de huit secondes. Si le choix échoue, la règle locale garde la main sur cette décision. »

## 9. Chester · Commenter les actions du match · 3:25–3:45 · B

- « Chester dispose de get_match_context, un outil LangChain qui lit le score, le chrono et les derniers événements confirmés. »
- « Le modèle demande explicitement cet outil. Le backend fournit le résultat, puis le modèle écrit sa réaction. »
- [Pointer la trace.] « Ici, le contexte d’un but donne un score de un partout à cinq minutes quarante-cinq. La réaction reprend l’égalisation. »

## 10. Mode Neuille · 3:45–4:00 · B

- « Le choix dans le salon change les consignes de style du prompt. On garde le même modèle et le même outil de lecture du match. »
- « En mode Neuille, on fournit des accroches, un exemple et une limite de dix mots. Le backend vérifie le format JSON, puis la longueur, l’accroche et l’absence de répétition. »
- « On personnalise ainsi la génération par le prompt, sans réentraîner le modèle. »

## 11. La démonstration · A

- [Annoncer Occulte contre Zeus, puis ouvrir le salon.]

## 12. Démo · 4:00–7:00 · A puis B

- [Vidéo de secours, 32 s.] Elle montre la consigne traitée par le coach, le dialogue lancé et un dribble choisi en mode IA puis exécuté dans le jeu.

- [A ouvre le salon dans un autre onglet.] Saisir « Fais s’affronter Occulte et Zeus. » Montrer les deux équipes sélectionnées et le dialogue généré.
- [A clique sur **Lancer le dialogue**.] « Le backend a préparé la rencontre. Les répliques s’affichent maintenant dans le jeu. » Avancer jusqu’au match.
- [B sélectionne **Pilote IA** dans **Options**.] Cliquer sur **L’agent joue pour moi**, puis montrer une action exécutée, idéalement une transition de menu pendant un duel.
- [B vérifie la source de la décision si la trace est ouverte.] Une décision marquée `mode: "text"` vient du modèle. Si le tour a utilisé une règle, dire « ici, le pilote est passé par la règle locale ».
- [B garde les sous-titres actifs.] Sur un événement confirmé, montrer `get_match_context`, le score et la réaction si la ligne apparaît. Sinon, revenir à la trace de la slide 6 et préciser qu’elle vient d’un essai antérieur.
- [B clique sur **Reprendre la main**.] Revenir au diapo après un effet visible, même si le match est encore en cours.

## 13. Le bilan · A

- [Passer au bonus MCP.]

## 14. Bilan · 7:00–8:00 · A puis B

- **A** · « En bonus, un serveur MCP permet à un client externe d’appeler la même API. Il peut par exemple observer la session avec observe_match. »
- **B** · « La limite principale est la couverture du jeu libre. Si le worker ne reconnaît plus de situation exploitable, le pilote peut rendre la main. »
- **B** · « On étendrait la reconnaissance des situations de jeu libre, puis on rejouerait les mêmes séquences pour mesurer les blocages et les actions exécutées. »

## Questions possibles

- **Pourquoi parler de trois agents avec un seul modèle ?** Les déclencheurs, les données, les schémas de sortie et les responsabilités diffèrent. Le même moteur sert à la génération.
- **Qui appelle réellement un outil ?** Chester appelle directement `get_match_context` via `bind_tools`. Le coach et le pilote rendent un résultat structuré, puis le backend déclenche `prepare_match` ou `apply_match_action` après validation.
- **D’où vient l’état du match ?** Le worker lit en mémoire les données reconnues, dont le score et le chrono. Il utilise aussi des signatures de pixels pour identifier certains menus.
- **Comment le contrôle est-il rendu au joueur ?** « Reprendre la main » annule la délégation. Avant d’envoyer une action, le backend vérifie encore que le pilote a le contrôle.
- **Que fait Celia ?** Elle résout une demande de recrutement. Le joueur confirme avant l’enregistrement de la recrue. Le parcours utilise une recherche déterministe dans le catalogue de la ROM.
- **RAG ?** Le match est lu via un outil applicatif. Le bonus présenté est le serveur MCP.

## Avant de projeter

- Ouvrir `docs/soutenance/index.html` dans le navigateur. Flèches pour naviguer et **F** pour le plein écran.
- Lancer InazumIA et vérifier que LM Studio sert le modèle configuré. Garder le salon ouvert dans un autre onglet.
- Refaire une fois Occulte–Zeus. Repérer un duel avec plusieurs choix et un événement qui déclenche Chester. Garder la trace d’un vrai appel et une capture de secours.
- En cas d’échec du coach, préparer Occulte–Zeus manuellement et préciser le mode utilisé. Le pilote déterministe peut aussi montrer une entrée DS si le modèle ne répond pas.
- Les captures du duel illustrent deux états réels du jeu. La slide Chester cite une trace locale conservée dans `build/agents/fe9c1c69e79c44979d5df8ad458c3a93/`.
