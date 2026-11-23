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

Ouvrez le salon avec **Lancer InazumIA.cmd**, puis choisissez **Entrer dans le
local**. Déplacez-vous jusqu’à Hillman avec les flèches ou ZQSD, puis appuyez
sur **A** pour lui parler. Répondez **Oui** pour ouvrir la route native.
Touchez un écusson sur l’écran inférieur et confirmez la rencontre.

- Occulte contre Zeus
- Royal Academy contre Raimon

**Options → Retour à la route** revient au tableau. Depuis le résultat, la
touche **A** permet aussi de revenir à la route. **Options → Fermer** rend
l’accès au salon, où les six équipes restent sélectionnables pour un match
personnalisé.

### Recrutement spécial

Depuis le salon web, écris « Raimon peut recruter Xene » à Celia dans
son panneau de recrutement. Tu peux soumettre un autre nom ou annuler le brouillon, puis
cliquer sur **Recruter**. La recrue rejoint son équipe à la prochaine
préparation d'un match en arène, à domicile comme à l'extérieur. Elle sera
aussi disponible pour les matchs du Club à la prochaine ouverture via
**Ouvrir le Club des recrues**, dans le panneau de Celia.
La première recrue rejoint également le groupe qui se déplace dans le local.
Pour l'inscrire pendant une session Club déjà ouverte, avance devant le coach
avant de confirmer.

Les six équipes du salon peuvent recruter jusqu’à onze joueurs chacune. Celia reste disponible après chaque confirmation. Le salon accepte
les fautes proches et demande une précision quand plusieurs noms correspondent. La recrue arrive au niveau 30 avec les
statistiques, techniques et visuels du joueur d'origine.

Choisis **Mon équipe du Club** chez le coach pour jouer avec l’équipe du
dernier recrutement et ses recrues. L'adversaire est Zeus, ou Raimon si Zeus a
recruté. **Retour au local** restaure l'effectif du Club.

La reprise du Club web lit `build/club/recruitment.save`. Cette archive
locale lie les fiches confirmées, le hash de la ROM Club et l'état natif. La
confirmation construit une ROM propre à la session. Le profil Club autonome
et la ROM source restent indépendants de cette sauvegarde.

La ROM française BEBF révision 0 a pour SHA-256
`1e67c699a6b3ecfb5230e8c2245746879fab57123277651da74b4cc9b8ba25d3`.
Elle contient 2 400 lignes dans chacune des tables mesurées du catalogue.
Les identifiants de `unitno.dat` et ceux au décalage 66 de `unitbase.dat`
concordent. Les lignes 2064 à 2399 portent l'identifiant zéro. La première
recrue utilise la ligne 2064 et l'identifiant 2931, qui suit le dernier
identifiant d'origine (2930). Le patch conserve les longueurs et modifie
la ligne correspondante dans `unitbase.dat` (96 octets), `unitno.dat`
(2 octets), `unitbase.STR` (128 octets) et les deux tables `unitstat.dat`
(80 octets par ligne). Le chargement d'un état antérieur exige aussi
d'actualiser l'unique copie mesurée de `unitno.dat` en RAM ARM9.

Le test dédié a vérifié Camille Azur (nom court Camille), unité 2931,
niveau 12, avec le cœur melonDS 0.9.3 (`4081e83`). La ROM Club
reconstruite pour cette fiche a pour SHA-256
`26846f2d4c415218ed41ff7d55430e0fada9a1d5eacd6c802e734fc7186b3c82`.
Le test vérifie l'annulation, le rejet d'une version obsolète, le retour à
l'état précédent après un échec, la confirmation répétée, la présence de la
recrue sur le terrain, le retour au local et la réouverture complète du worker.

Vérifications reproductibles :

```powershell
python -m unittest discover -s tests -q
python tests/smoke_club.py
python tests/smoke_native_club.py
python tests/smoke_recruitment_rom.py
```

Le smoke test nécessite la ROM et le cœur melonDS locaux attendus par le projet.
