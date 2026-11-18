# Matchs amicaux du club

## Lancer sans navigateur

**Ouvrir le Club dans melonDS.cmd** construit le profil `club_native` et ouvre
sa ROM dans `melonDS.exe`. Dans la cour devant le local, l'objet lumineux
lance le Défi Mystère. Parler à Seymour puis répondre Oui
ouvre une route native de deux rencontres : **Occulte vs Zeus** et
**Royal Academy vs Raimon**. Toucher un écusson, puis confirmer le lancement.
Les deux cases sont accessibles immédiatement et réutilisent des écussons
du jeu. Les intitulés désignent les affiches ; les matchs conservent les noms
et effectifs réels des équipes, indépendamment du groupe d'exploration.

Cette ROM fonctionne sans navigateur ni pilote InazumIA. Elle utilise une
partie isolée, sans import de sauvegarde de campagne. La construction exige
`ndspy==4.2.0` (`python -m pip install -r requirements-rom.txt`), également
accepté depuis `local/python-deps`. Le retour natif après un match restaure
les cinq joueurs d'exploration ; son déroulement complet reste à valider.

## Jouer dans le navigateur

Double-cliquer **Lancer InazumIA.cmd** pour ouvrir la page InazumIA.

Maintenir les flèches ou ZQSD pour marcher, même après avoir cliqué un bouton.
La croix directionnelle accepte aussi un appui prolongé à la souris ou au
doigt. Dans le local, maintenir le stylet sur l'écran inférieur fait marcher
Mark vers le point indiqué. Relâcher ou quitter la fenêtre arrête l'appui.

Dans le lanceur InazumIA, fermer la session éventuelle puis choisir **Entrer
dans le local**. Avancer vers Hillman et lui parler avec **A** ou l'écran
tactile. Aucun agent IA n'est nécessaire pour ces rencontres.

Le PNJ propose, avec le sélecteur Oui/Non natif :

- Occulte contre Zeus ;
- Royal Academy contre Raimon ;
- Zeus contre Occulte ;
- Raimon contre Royal Academy.

**Non** passe à l'affiche suivante. Refuser les quatre offres rend la main
dans la pièce. **Oui** prépare les effectifs, puis A avance les six répliques
des capitaines et lance le vrai match. Les équipes sont celles du catalogue
d'origine, avec leurs remplaçants disponibles ; le groupe d'exploration ne
participe pas à leur place.

Le profil `club` réutilise le moteur dynamique de `develop` : slots SSD/SST
bornés, chargement natif du match, worker melonDS isolé et arrêt sur le
résultat final natif. A après le résultat, ou **Retour au local**, restaure
l'état précédant la conversation : position, groupe et effectif d'exploration.
Les gains des équipes invitées ne sont pas transférés au groupe du joueur.
Le retour direct d'une ROM seule reste soumis à la limitation documentée dans
`DELIVERY.md` ; utiliser le lanceur fourni.

La ROM BEBF fournie ne contient pas de local de club intact. Ce profil réemploie
l'intérieur natif `mr07i01`, renommé « Local du club », avec un PNJ Hillman.
Il ne remplace ni les cartes ni les événements du profil scénario historique.

Le premier accès construit `build/club/arena.nds` une seule fois à partir de
`rom/original.nds`. Changer d'affiche ne reconstruit pas la ROM. Raimon adverse
utilise une copie isolée de son effectif complet dans le profil amical ;
l'équipe de départ conserve son propre modèle. Aucun asset du jeu, ROM ou
savestate ne doit être ajouté au dépôt.

Vérifications reproductibles :

```powershell
python -m unittest discover -s tests -q
python tests/smoke_club.py
python tests/smoke_native_club.py
```

Le smoke test nécessite la ROM et le cœur melonDS locaux attendus par le projet.
