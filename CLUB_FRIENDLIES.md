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

Vérifications reproductibles :

```powershell
python -m unittest discover -s tests -q
python tests/smoke_club.py
python tests/smoke_native_club.py
```

Le smoke test nécessite la ROM et le cœur melonDS locaux attendus par le projet.
