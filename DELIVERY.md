# Livraison InazumIA — branche develop

## Utilisation

1. Double-cliquer **Lancer InazumIA.cmd**.
2. Écrire **Fais s'affronter Occulte et Zeus** dans le chat.
3. Attendre « Rencontre prête », puis lancer le dialogue ou appeler l'agent joueur.
4. Jouer avec les commandes DS du navigateur, ou laisser l'agent agir.
5. Reprendre la main à tout moment. « Nouvelle rencontre » prépare le prochain
   match dans la même session, depuis son checkpoint initial.

Le bouton **Entrer dans le local** ouvre aussi les amicaux proposés par Hillman,
avec Occulte–Zeus et Royal Academy–Raimon dans les deux sens, indépendamment du
groupe d'exploration. Voir [CLUB_FRIENDLIES.md](CLUB_FRIENDLIES.md).

La livraison propose Raimon, Royal Academy, Occulte et Zeus, leurs effectifs
natifs et leurs capitaines. Les six répliques apparaissent dans le jeu avant
le lancement football. Le serveur MCP tourne sur le PC et pilote le même worker
que le navigateur. Les rencontres sont configurées en RAM ; aucune compilation
de ROM par affiche n'est nécessaire.

## Prérequis

- Windows, Python 3.11+ ; cette livraison est testée avec Python 3.12.
- Votre original BEBF révision 0 dans `rom/original.nds`, SHA-256
  `1e67c699a6b3ecfb5230e8c2245746879fab57123277651da74b4cc9b8ba25d3`.
- Le cœur déjà installé dans `local/tools/melonds-core/melonds_libretro.dll`,
  SHA-256 `e50e675eab350e14d1cb9ccc4ada7f09fb6a3e6dcd16ef4a197d9a5b8a656f13`.
  Un autre cœur est rejeté pour éviter d'utiliser des adresses non validées.
- Codex CLI installé et connecté pour l'organisateur et le joueur visuel.
  La préparation et le contrôle manuels n'appellent pas de modèle.
- Pour MCP uniquement, suivre les commandes d'installation de WEB_AND_MCP.md.

Le dossier de travail possède déjà la ROM et le cœur privés. Le ZIP source ne
contient ni ROM, ni DLL, ni sauvegardes, ni credentials. Sur une autre machine,
ces prérequis doivent être apportés séparément. Le script historique
`src/setup_tools.py` aide à récupérer les outils officiels ; une archive nightly
différente ne remplace pas automatiquement le cœur validé ci-dessus.

## Construction et contenu

Le lanceur vérifie l'identité des sources et de la ROM d'arène. Si nécessaire,
`src/prepare_arena.py` reconstruit uniquement cette coque fixe depuis l'original.
Les buffers SSD/SST et les en-têtes d'équipes sont ensuite préparés à chaud,
avec contrôle des tailles, de la phase, du hash et lecture de vérification.

Le build d'arène et son rapport de réversibilité restent dans `build/arena/`.
L'écran final natif est conservé par le contrôleur, qui assure ensuite le retour
au salon par checkpoint ; le retour direct de la ROM dans un frontend autonome
n'est pas pris en charge. L'arène constitue un composant du système web/MCP livré.
`python src/package_release.py` produit `dist/InazumIA-develop-source.zip`,
avec un manifeste SHA-256 interne. Les preuves privées ne sont pas empaquetées.

Voir [WEB_AND_MCP.md](WEB_AND_MCP.md) pour les commandes, le protocole et les logs,
et [DELIVERY_VERIFICATION.md](DELIVERY_VERIFICATION.md) pour la portée des essais.
