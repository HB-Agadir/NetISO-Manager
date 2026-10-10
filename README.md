# NetISO Manager

Jouez a vos ISO Xbox 360 stockes sur un PC Windows, directement depuis la liste de jeux d'Aurora, sur une console RGH/JTAG.

Chaque ISO du PC apparait dans Aurora comme un jeu installe, avec sa pochette et son titre. Un appui sur A monte l'ISO par le reseau et demarre le jeu. Le bouton Guide et le retour a Aurora fonctionnent normalement.

## Ce que fait l'application

- Choix d'un ou plusieurs dossiers d'ISO, sur n'importe quels disques du PC, sous-dossiers compris.
- Lecture du Title ID et du Media ID dans chaque ISO (XGD2, XGD3, XISO).
- Creation d'une tuile par jeu et envoi sur la console par le FTP d'Aurora, avec verification de chaque fichier.
- Serveur NetISO integre, qui sert les jeux de tous les dossiers a la fois.
- Detection automatique: quand un ISO est ajoute ou retire d'un dossier, l'application le signale et propose de le transferer vers Aurora.
- Une seule tuile par jeu, meme s'il tient sur plusieurs disques. Le disque se choisit depuis la console, en maintenant la gachette droite (disque suivant) ou gauche (disque precedent) au lancement de la tuile, ou dans l'application.
- Gestion des doublons: un jeu deja installe sur la console garde la priorite et ne recoit pas de tuile. Si vous le supprimez de la console, sa tuile NetISO revient a la synchronisation suivante.
- Installation du plugin sur la console en un clic (adresse du PC et `launch.ini`).
- Affichage du jeu en cours et du debit, demarrage avec Windows.
- Interface en francais, anglais et arabe.

## Prerequis

- Une Xbox 360 RGH ou JTAG avec DashLaunch et Aurora 0.7b.
- Le plugin `NetISO.xex` 1.0 de cOz, charge par DashLaunch. Il n'est pas fourni ici.
- Un PC Windows avec Python 3 (Tkinter inclus), sur le meme reseau que la console.
- Vos propres ISO, issus de jeux que vous possedez.

## Installation sur la console

1. Copiez `NetISO.xex` sur la console, par exemple dans `Hdd1:\Apps\`.
2. A cote, creez `NetISO.xex.txt` contenant uniquement l'adresse IP du PC. L'application affiche cette adresse dans la zone Serveur.
3. Dans `launch.ini`, section `[Plugins]`, ajoutez le plugin sur une ligne libre:
   ```
   plugin4 = Hdd:\Apps\NetISO.xex
   ```
4. Redemarrez la console.
5. Dans Aurora, ajoutez `Hdd1:\NetISO` aux chemins de scan des jeux, avec une profondeur d'au moins 2.

Le Nova.xex modifie de la methode NetISO classique n'est pas necessaire.

## Utilisation

1. Lancez `NetISO Manager.bat`.
2. Ajoutez vos dossiers d'ISO.
3. Renseignez l'adresse IP de la console et, si besoin, les identifiants FTP d'Aurora.
4. Cliquez sur "Synchroniser avec Aurora", Aurora etant ouvert sur la console.
5. Lancez un scan dans Aurora, puis un jeu.

Laissez l'application ouverte pendant que vous jouez: c'est elle qui sert les ISO. PC eteint, les jeux installes sur la console fonctionnent toujours; les tuiles NetISO restent visibles mais ne se lancent pas.

## Fonctionnement

Le plugin `NetISO.xex` sait presenter un ISO distant comme un disque dans le lecteur, mais il faut passer par le gestionnaire de fichiers pour choisir le jeu. NetISO Manager remplace cette etape:

- chaque tuile est un petit lanceur (`stub/`) qui porte le Title ID du jeu, ce qui permet a Aurora de l'identifier;
- au lancement, il demande au plugin de monter son ISO, attend que le disque soit lisible, puis demarre le jeu;
- le serveur integre (`app/netiso_server.py`) parle le protocole du serveur NetISO d'origine.

Les details techniques, dont les obstacles rencontres, sont dans [docs/NOTES_TECHNIQUES.md](docs/NOTES_TECHNIQUES.md).

## Limites connues

- Le port TCP 4323 est impose par le plugin. Si un autre programme l'occupe (un antivirus, par exemple), le serveur ne peut pas demarrer.
- Le debit est limite par le port Ethernet 100 Mbit/s de la console.
- Le lanceur n'agit que sur la version 1.0 du plugin. Sur une autre version il ne modifie rien, et le bouton Guide peut alors rester inactif apres un lancement.
- Les title updates et le changement de disque des jeux multi-disques n'ont pas encore ete valides.
- Teste sur une seule console: Trinity, dashboard 17559, Aurora 0.7b.2.

## Compiler le lanceur

`app/stub.xex` est fourni compile. Pour le recompiler: Visual Studio avec le SDK Xbox 360, configuration `Release Retail | Xbox 360`, et la bibliotheque xkelib. Le chemin vers xkelib est a ajuster dans `stub/stub.vcxproj` (propriete `XkelibDir`).

## Tests

```
python app/tests/test_core.py
python app/tests/test_app.py
```

## Soutenir le projet

NetISO Manager est gratuit et le restera. S'il vous est utile, vous pouvez soutenir son developpement: https://ko-fi.com/x360remap

## Credits

- cOz pour le plugin NetISO et DashLaunch.
- tuxuser pour `netiso-srv`, dont le code a servi de reference pour le protocole.
- Phoenix pour Aurora.
