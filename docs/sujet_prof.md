# Concevoir une application augmentée par des agents IA

## Pitch
Par binôme, imaginez et développez une application avec un frontend et un backend, puis donnez-lui une véritable capacité d’action grâce à une architecture d’au moins trois agents construite avec LangChain. Les agents ne doivent pas se limiter à produire des réponses : ils doivent utiliser des outils pour consulter ou modifier des éléments réels de l’application. Le sujet est libre, à condition de faire valider en amont le besoin retenu et l’architecture multiagent.

## Descriptif du projet
Vous allez concevoir une application répondant à un besoin concret, réel ou fictif. Le domaine est libre : organisation, éducation, culture, commerce, mobilité, santé, environnement, productivité, etc. Le projet doit comporter un frontend et un backend, et intégrer une architecture multiagent reposant sur LangChain.

### Exigences obligatoires
- **Une application utilisable**, avec un frontend et un backend qui communiquent.
- **Au moins trois agents distincts**, avec des responsabilités clairement définies et complémentaires.
- **Une orchestration explicite** : montrer comment une demande est distribuée entre les agents et comment leurs résultats sont exploités.
- **Des outils réellement utilisables par les agents** : par exemple, appeler une API, effectuer une recherche, consulter ou modifier des données de l’application, créer un élément, déclencher une action métier ou mettre à jour un état.

Les agents doivent contribuer au fonctionnement de l’application : une simple succession de prompts, ou plusieurs agents qui ne font que générer du texte, ne suffit pas. Les outils doivent être reliés au backend ou à un service réellement utilisé par l’application ; des actions entièrement simulées ne démontrent pas une intégration effective.

### Bonus techniques
Les éléments suivants sont facultatifs et peuvent apporter des points bonus :
- **MCP** : implémenter un serveur MCP exposant des outils, ou intégrer un client MCP dans l’application.
- **RAG** : donner aux agents accès à une base documentaire pertinente par recherche augmentée.

## Validation du sujet et de l’architecture
Avant de développer, chaque binôme présente brièvement à l’enseignant le projet

## Soutenance
La soutenance dure **5 à 10 minutes**, puis se poursuit par des questions de l’enseignant. Elle est réalisée en binôme ; les deux membres doivent pouvoir expliquer le projet et ses choix.

1. **Architecture** : présenter le diagramme, les rôles des agents, l’orchestration et les outils.
2. **Démonstration** : suivre un scénario de bout en bout et rendre visible l’action d’un agent dans l’application.
3. **Bilan** : indiquer une limite et une piste d’amélioration.
4. **Questions** : répondre sur l’architecture, les choix techniques et le fonctionnement réel des outils.

Préparez un scénario de démonstration fiable et des données adaptées. Une vidéo ou des captures peuvent aider en cas de problème technique, mais ne remplacent pas la démonstration de l’application.


## Notation — sur 20

| Critère | Points | Éléments évalués |
|---|---:|---|
| Application | 4 | Frontend et backend fonctionnels, application cohérente avec le besoin. |
| Architecture multiagent | 5 | Au moins trois agents distincts ; architecture claire, illustrée par un diagramme et expliquée à l’oral. |
| Outils et actions des agents | 6 | Les agents utilisent des outils connectés à l’application ou à un service, et réalisent des actions visibles — pas seulement des réponses textuelles. |
| Démonstration et soutenance | 5 | Démonstration compréhensible, respect du format, participation des deux membres et réponses aux questions. |
| **Total** | **20** | |
