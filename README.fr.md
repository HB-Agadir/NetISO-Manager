# NetISO Manager

<img src="icon.png" alt="NetISO Manager" width="128">

[English](README.md) | Francais

Jouez a vos ISO Xbox 360 stockes sur un PC Windows, directement depuis la liste de jeux d'Aurora, sur une console RGH/JTAG.

**Gratuit et open source.** Si ce logiciel vous est utile, vous pouvez soutenir son developpement: **[ko-fi.com/x360remap](https://ko-fi.com/x360remap)**

Chaque ISO du PC apparait dans Aurora comme un jeu installe, avec sa pochette et son titre. Un appui sur A monte l'ISO par le reseau et demarre le jeu. Le bouton Guide et le retour a Aurora fonctionnent normalement.

## Ce que fait l'application

- Choix d'un ou plusieurs dossiers de jeux, sur n'importe quels disques du PC, sous-dossiers compris.
- Accepte les fichiers ISO et les dossiers de jeu extraits (un dossier contenant `default.xex`). Un dossier est presente a la console comme un disque, a la volee: rien n'est converti ni copie, et le debit est le meme qu'avec un ISO.
- Lecture du Title ID et du Media ID dans chaque ISO (XGD2, XGD3, XISO).
- Creation d'une tuile par jeu et envoi sur la console par le FTP d'Aurora, avec verification de chaque fichier.
- Serveur NetISO integre, qui sert les jeux de tous les dossiers a la fois.
- Detection automatique: quand un ISO est ajoute ou retire d'un dossier, l'application le signale et propose de le transferer vers Aurora.
- Une seule tuile par jeu, meme s'il tient sur plusieurs disques. Le disque se choisit depuis la console, en maintenant la gachette droite (disque suivant) ou gauche (disque precedent) au lancement de la tuile, ou dans l'application.
- Gestion des doublons: un jeu deja installe sur la console garde la priorite et ne recoit pas de tuile. Si vous le supprimez de la console, sa tuile NetISO revient a la synchronisation suivante.
- Installation du plugin sur la console en un clic (adresse du PC et `launch.ini`).
- Chargements rapides: environ deux fois le debit de NetISO d'origine (8,9 Mo/s mesures contre 4,1).
- Affichage de l'ecran de la console dans une fenetre du PC, pour suivre l'installation sans changer d'entree HDMI.
- Affichage du jeu en cours et du debit, demarrage avec Windows.
- "Tester ma configuration": verifie le serveur, le type de reseau Windows, la console, le plugin et l'adresse qu'il utilise, et dit quoi corriger. Copie un rapport de diagnostic pour les forums, sans mot de passe, adresse ni nom d'utilisateur.
- Recherche de la console sur le reseau: plus d'adresse IP a taper.
- Suivi de l'adresse du PC: quand la box en donne une nouvelle au PC, l'application l'ecrit seule sur la console.
- Le PC ne se met pas en veille pendant une partie.
- Lancement d'un jeu sur le PC dans l'emulateur Xenia (non fourni), en un clic.
- Vue "Available games" dans Aurora: les jeux du PC sont masques quand le serveur ne tourne pas, ainsi que les disques d'installation et les packs de voix. Mise en place par un script Aurora facultatif, "NetISO Setup". L'application relance Aurora quand le serveur demarre ou s'arrete, seulement si Aurora est a l'ecran, pour que la liste suive.
- Les tuiles multi-disques demarrent sur le disque de jeu, pas sur un disque d'installation ou de voix.
- Verification de chaque ISO: les fichiers incomplets (telechargement ou copie interrompu) sont signales avant d'arriver sur la console.
- Proposition de passer en "Prive" un reseau Windows classe "Public" (le pare-feu bloque sinon la console), par la fenetre administrateur de Windows.
- Numero de version dans le titre de la fenetre. Version portable (zip) a cote de l'installateur.
- Avis de nouvelle version. Cette verification, une requete a GitHub au demarrage, est le seul acces de l'application a Internet; rien sur vous n'est envoye.
- Interface en francais, anglais et arabe.

## Prerequis

- Une Xbox 360 RGH ou JTAG avec DashLaunch et Aurora 0.7b.
- Le plugin `NetISO.xex` 1.0 de cOz. Il est fourni avec NetISO Manager, sans modification, et installe par le bouton de configuration.
- Un PC Windows 64 bits sur le meme reseau que la console. L'installateur `NetISOManager-x64.msi` des releases contient tout, guide d'utilisation compris; pour lancer depuis les sources il faut Python 3 (Tkinter inclus).
- Vos propres ISO ou dossiers de jeu, issus de jeux que vous possedez.

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

1. Installez `NetISOManager-x64.msi` puis lancez NetISO Manager depuis le Bureau (ou `NetISO Manager.bat` depuis les sources).
2. Ajoutez les dossiers qui contiennent vos jeux.
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
- Le debit est limite par le port Ethernet 100 Mbit/s de la console. Les chargements rapides atteignent environ 8,9 Mo/s.
- La fenetre d'ecran de la console affiche une image toutes les trois secondes environ. C'est une aide a l'installation, pas un flux video.
- Le lanceur n'agit que sur la version 1.0 du plugin. Sur une autre version il ne modifie rien, et le bouton Guide peut alors rester inactif apres un lancement.
- Le disque d'un jeu multi-disques se choisit au lancement de la tuile. Changer de disque sans quitter le jeu n'est pas possible.
- L'application des title updates aux jeux lances par NetISO n'a pas encore ete verifiee.
- Teste sur une seule console: Trinity, dashboard 17559, Aurora 0.7b.2.

## Compiler le lanceur

`app/stub.xex` est fourni compile. Pour le recompiler: Visual Studio avec le SDK Xbox 360, configuration `Release Retail | Xbox 360`, et la bibliotheque xkelib. Le chemin vers xkelib est a ajuster dans `stub/stub.vcxproj` (propriete `XkelibDir`).

## Construire l'installateur

`build_msi.bat` cree `dist\NetISOManager-<version>-x64.msi` avec PyInstaller et WiX 5. L'installateur pose l'application dans `Program Files`, cree les raccourcis (application et guides), et ajoute une regle de pare-feu limitee a ce programme, au port TCP 4323, aux reseaux prives et au sous-reseau local. `build_exe.bat` produit a la place un executable unique, portable.

Le guide d'utilisation est dans `docs/` (francais et anglais).

## Tests

```
python app/tests/test_core.py
python app/tests/test_app.py
python app/tests/test_cleanup.py
python app/tests/test_folders.py
python app/tests/test_nova.py
```

## Soutenir le projet

NetISO Manager est gratuit et le restera. S'il vous est utile, vous pouvez soutenir son developpement par un don:

**[ko-fi.com/x360remap](https://ko-fi.com/x360remap)**

Le lien est aussi dans l'application ("Soutenir le projet", en haut de la fenetre) et dans le guide d'utilisation. Du meme auteur: [X360Remap](https://github.com/HB-Agadir/X360Remap).

## Remerciements

NetISO Manager ne fait que rendre plus simple un travail que d'autres ont accompli. Sans eux, il n'existerait pas.

- **cOz**, auteur du plugin NetISO et de DashLaunch. C'est son plugin qui fait croire a la console qu'un disque est dans le lecteur: tout le reste repose dessus. Merci aussi a ceux qu'il remercie lui-meme dans son fichier d'origine: SpkLeader, Swizzy, Phoenix, vgcrepairs, Team Xecuter, RF1911 et tydye.
- **ConfusionRS**, pour la distribution de NetISO adaptee a Aurora 0.7b, qui a fait connaitre et fonctionner cette methode sur les consoles d'aujourd'hui.
- **tuxuser**, pour `netiso-srv`, le serveur libre dont le code a servi de reference pour le protocole.
- **muradbu**, pour le projet `netiso`, qui a montre l'idee d'un lanceur par jeu reconnu par Aurora.
- **Team Phoenix**, pour Aurora et son systeme de scripts, utilise ici pour nettoyer la liste des jeux.
- **Warranty Voider (zeroKilo)** et **SaveEditors**, pour XEXLoaderWV, et l'equipe de **Ghidra**: les outils qui ont permis de comprendre comment dialoguer avec le plugin.
- Les auteurs de **xkelib**, utilisee pour compiler le lanceur.
- La communaute **ConsoleMods** pour sa documentation.

NetISO Manager n'est affilie a aucun d'entre eux.

**A propos du plugin fourni.** `app/plugin/NetISO.xex` est le NetISO 1.0 de cOz, inclus exactement tel qu'il l'a publie, avec son fichier d'origine (`app/plugin/NetISO-README-cOz.txt`). Il est joint pour une seule raison: le lanceur ne fonctionne qu'avec cette version precise, et demander aux debutants de trouver le bon fichier ailleurs etait le principal obstacle a l'installation. Il reste entierement son oeuvre. Si cOz ou tout ayant droit prefere qu'il ne soit pas distribue ici, ouvrez un ticket et il sera retire.

## Licence

NetISO Manager est distribue sous licence GNU GPL version 3: voir le fichier `LICENSE`. Vous pouvez l'utiliser, le modifier et le redistribuer, a condition de conserver cette licence et de publier vos sources.
