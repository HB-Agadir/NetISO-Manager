# Notes techniques

## Objectif

Sur une Xbox 360 RGH, afficher tous les jeux ISO stockes sur le PC dans la liste de jeux d'Aurora (jaquettes, title updates, DLC), et lancer un jeu en un clic. A la sortie du jeu, l'ISO est libere et un autre peut etre lance.

## Etat

Fonctionnel sur la console de test (2026-10-10): application Windows NetISO Manager, lanceur par jeu, serveur integre, gestion des doublons.

## Pistes etudiees

### A. Stubs par jeu + plugin NetISO (piste privilegiee)

- Un generateur PC cree un mini `.xex` par ISO, avec le Title ID et le Media ID du jeu.
- Aurora scanne ces stubs comme des jeux installes.
- Au lancement, le stub demande au plugin NetISO de monter l'ISO, puis demarre `default.xex`.
- Reference: https://github.com/muradbu/netiso (MIT). Limite annoncee par ce projet: sans pilote DVD virtuel kernel, le jeu ne lit plus le disque apres `default.xex`.
- Serveur PC existant: https://github.com/tuxuser/netiso-srv (port TCP 4323).

### B. Systeme de fichiers virtuel + ConnectX (ecartee pour l'instant)

- Le PC presente les ISOs comme des dossiers extraits via un partage SMB, lu par ConnectX.
- Ecartee: retours d'utilisateurs indiquant des saccades sur les jeux a milliers de petits fichiers (environ 5 Mo/s), et ConnectX exige SMBv1.

## Contraintes connues

- Ethernet de la 360: port 10/100, limite materielle (environ 11 a 12 Mo/s en pratique).
- Un seul lecteur DVD virtuel: un seul ISO monte a la fois.

## Analyse de NetISO.xex (Ghidra 12.1.3 + XEXLoaderWV)

Decompilation complete dans `analysis/NetISO.xex.dump.txt`. Auteur: cOz (README du plugin), 2015.

- Le plugin cree un peripherique `\Device\NetIso` qui se comporte comme un systeme de fichiers, et accroche `\Device\Cdrom0` pour servir l'ISO monte.
- Il ne possede aucune fonction exportee. Le montage se commande uniquement en parcourant ce peripherique:
  - profondeur 1 (racine): liste des ISOs du serveur, precedee de `[Disable Current ISO]` quand un ISO est monte;
  - profondeur 2 (dans un ISO): une seule entree, `Mount`;
  - profondeur 3 (dans `Mount`): l'enumeration envoie la commande de montage au serveur.
- Protocole reseau: en-tete de 20 octets, magic `ISVR`, commandes 0 ping, 1 et 2 geometrie, 3 lecture, 4 index, 5 montage. Lectures par blocs de 4096 octets maximum.
- Config: IP du serveur lue dans `netiso.xex.txt` a cote du plugin ou a la racine du disque interne.

Consequence: un stub peut monter un ISO en ouvrant `\Device\NetIso\<nom>\Mount` et en listant ce dossier, sans modifier le plugin. Les chemins exacts restent a confirmer sur la console.

## Phase 0: resultat (2026-10-10)

Valide sur console: un stub XEX lance depuis sa tuile Aurora monte l'ISO et demarre le jeu en un clic (`stub/`, build 5).

- Montage: enumerer `netiso:\<nom>\Mount\*` apres avoir lie `netiso:` a `\Device\NetIso`. Le serveur repond en quelques millisecondes.
- Le plugin simule ensuite l'ouverture puis la fermeture du tiroir. Le systeme ferme alors tout titre qui n'a pas le privilege XEX `NO_FORCE_REBOOT` (`<privilege id="0"/>` dans `xex.xml`). Sans lui, le stub est coupe en moins de 500 ms et la console revient a Aurora.
- Avec ce privilege, le stub attend que `\Device\Cdrom0\default.xex` soit lisible puis appelle `XLaunchNewImage`.
- Juste apres un montage, le plugin appelle xam (instruction `bl` en 0x91104DC4, opcode 0x48007369, cible xam 0x816C8890 sur le dashboard 17559). Si cet appel a lieu alors que le stub lance lui-meme le disque, le bouton Guide est ignore pour toute la session, y compris dans les jeux du disque dur, jusqu'au redemarrage. Les autres plugins (X360Remap, xbdm, JRPC2) et les noms des liens symboliques sont hors de cause.
- Correctif valide (build 7): remplacer ce `bl` par un `nop` (0x60000000) juste avant la demande de montage, puis remettre l'opcode d'origine juste apres. Le stub verifie l'opcode avant d'ecrire et ne touche a rien s'il ne correspond pas (autre version du plugin).
- Neutraliser cet appel sans le privilege `NO_FORCE_REBOOT` ne suffit pas (build 4): le stub est quand meme ferme par le tiroir simule.
- `launch.ini` doit declarer `NetISO.xex` dans `[Plugins]`, sinon `\Device\NetIso` n'existe pas (erreur 0xC000000D a la creation du lien).

Etat final de la phase 0: un clic sur la tuile lance le jeu, le bouton Guide fonctionne en jeu, le retour a Aurora fonctionne, et Guide fonctionne ensuite dans les autres jeux.

Outillage de test: XeCLI (`rgh`) via `xbdm.xex`. Envoyer avec `rgh fs put` puis verifier l'empreinte avec `rgh fs get`, lire le journal avec `rgh fs cat`, observer avec `rgh debug watch`. Des envois FTP manuels n'avaient pas remplace le fichier et ont fausse deux essais.

## NetISO Manager (application Windows)

Lancement: `NetISO Manager.bat`. Python 3 avec Tkinter, bibliotheque standard uniquement. Reglages dans `%APPDATA%\NetISOManager\settings.json`.

| Fichier | Role |
|---|---|
| `app/NetISOManager.pyw` | Interface: dossiers, liste des jeux, envoi vers la console, serveur |
| `app/netiso_iso.py` | Lecture des ISOs et fabrication des tuiles |
| `app/netiso_server.py` | Serveur NetISO integre, sert les jeux de tous les dossiers |
| `app/netiso_console.py` | Envoi des tuiles par le FTP d'Aurora, avec relecture et comparaison d'empreinte |
| `app/stub.xex` | Copie du lanceur compile (`stub/Release Retail/default.xex`) |
| `app/tests/test_core.py` | Tests unitaires (ISO et serveur) |

- Lecture d'un ISO: `default.xex` de la partition jeu (XGD3 en 0x2080000, XGD2 en 0xFD90000, XGD1 en 0x18300000, ou XISO brut), dont on extrait Title ID, Media ID et numero de disque.
- Une tuile = `default.xex` (le stub avec ces identifiants inscrits dans son en-tete d'execution) + `netiso.cfg` (nom du jeu). Ce nom est aussi celui que le serveur annonce a la console: ASCII, 42 caracteres au plus, unique. Le fichier ISO peut donc porter n'importe quel nom.
- Le serveur accepte aussi le nom du fichier ISO, pour les tuiles faites avec le serveur d'origine.
- Protocole du serveur (port TCP 4323): en-tete de 20 octets big-endian `ISVR`, commande u16, index u16, offset u64, longueur u32. 0 ping (`ISVRokOK`), 1 taille (secteurs, 0x800), 2 type (0), 3 lecture, 4 nom par index (vide = fin de liste), 5 montage (`\<nom>\Mount`, reponse 1 ou 0).

Doublons: la copie installee sur la console a la priorite sur l'ISO du PC. A chaque synchronisation, l'application cherche les jeux installes par FTP (un `default.xex` jusqu'a deux niveaux sous les dossiers de jeux de la console, par defaut `/Hdd1/Games`, plus les conteneurs GOD de `Content/0000000000000000/<TitleID>/00007000` ou `00004000`), compare par (Title ID, numero de disque), n'envoie une tuile que pour les jeux absents, et retire les tuiles devenues inutiles (jeu installe entre-temps, ou ISO supprime du PC). Une tuile n'est retiree que si son dossier contient `netiso.cfg`, et seuls `default.xex`, `netiso.cfg` et `netiso_stub.log` y sont supprimes. La base `content.db` d'Aurora n'est pas utilisable: elle est verrouillee tant qu'Aurora tourne.

Empreinte d'en-tete: Title ID et Media ID sont dans la partie hachee des en-tetes XEX. Apres les avoir inscrits il faut recalculer le champ HeaderHash (security info + 0x164), sinon la console plante au chargement (aucun journal n'est ecrit). HeaderHash = SHA-1 de `[security info + 0x17C, debut de l'image)` suivi de `[0, security info + 8)`. `stamp_stub` verifie d'abord qu'il sait reproduire l'empreinte du stub d'origine.

Valide sur console le 2026-10-10: tuile avec Title ID affichee avec sa pochette, lancee, ISO servi par le serveur integre depuis l'un des trois dossiers du PC (Binary Domain, `\Device\Cdrom0\default.xex`).

A valider: le comportement des title updates (le stub porte le meme Title ID et Media ID que le jeu).

## Evolutions du 2026-10-10 (soir)

- Une tuile par jeu: les disques d'un meme jeu (meme Title ID, plusieurs disques annonces) sont regroupes. La tuile lance le disque choisi dans l'application (bouton "Changer de disque", memorise par Title ID dans `active_discs`). Les disques qui sont des jeux distincts (Title ID differents) gardent chacun leur tuile et leur mention de disque.
- Noms: les mentions de region et de langues sont retirees; celles qui parlent de disque sont conservees.
- `netiso.cfg`: ligne 1 = nom de la tuile, ligne 2 = message a afficher sur la console si le PC est injoignable (UTF-8, dans la langue de l'application).
- Detection automatique des ISO ajoutes ou retires (sondage toutes les 15 s, attend la fin d'une copie), avec proposition de transfert.
- Interface en francais, anglais, arabe (`app/netiso_i18n.py`).
- Zone Serveur: jeu en cours et debit; demarrage avec Windows (cle Run de l'utilisateur, fenetre reduite).
- Bouton "Installer le plugin sur la console": envoie `NetISO.xex` s'il manque, ecrit l'adresse du PC dans `NetISO.xex.txt`, ajoute le plugin a `launch.ini` apres sauvegarde (`launch.ini.netiso.bak`). Non essaye sur une console non configuree.
- Lanceur 1.0 (`stub/main.cpp`): detecte l'absence de serveur (le plugin liste alors une seule entree `No Server!`) et met en file une notification avant de rendre la main. Compile, garde dans `deploy/stub_1.0_candidate.xex`, PAS ENCORE VALIDE sur console. `app/stub.xex` reste le build 7 valide; il ignore la ligne 2 de `netiso.cfg`.
- Changement de disque en cours de partie et demontage au retour dans Aurora: non realises, pas de declencheur fiable depuis le PC.

## Changement de disque depuis la console (2026-10-10)

- Mesure: ouvrir puis fermer le vrai tiroir (`rgh tray open/close`) pendant un jeu NetISO ne provoque aucune relecture du disque cote serveur (le descripteur de volume n'est relu qu'au montage et au lancement du titre). Le serveur ne peut donc pas deduire une demande de changement de disque, ni en imposer un: seule une commande de montage emise par la console declenche le cycle de tiroir simule.
- Realise: le lanceur 1.0 lit la manette au demarrage d'une tuile multi-disques (ligne 3 de `netiso.cfg` = nombre de disques, fenetre de 700 ms). Gachette droite ou clic du stick droit: disque suivant. Gachette gauche ou clic du stick gauche: disque precedent. Il ajoute alors `#+` ou `#-` au nom dans la demande de montage; le serveur avance le disque actif de la tuile, le memorise et le sert.
- Valide sur console: le suffixe traverse le plugin et le serveur monte le disque 2 (Wolfenstein - The New Order, 4 disques, une seule tuile). La lecture de la manette elle-meme reste a essayer en vrai.
- Lanceur 1.0 valide sur console pour le chemin normal et devient `app/stub.xex`. Non observes: la notification a l'ecran, et le cas d'un nom de jeu inconnu du serveur (retour a Aurora avant la fin de l'attente, sans message).
- Changement de disque sans quitter le jeu: demanderait un petit plugin resident qui emet la commande de montage sur un raccourci manette. Non realise.

## Questions ouvertes

1. Title updates: s'appliquent-ils a un jeu lance par une tuile qui porte le meme Title ID et Media ID?
2. Jeux multi-disques: comportement au changement de disque.
3. Le port 4323 peut etre pris par un autre programme du PC (constate avec `avp.exe` de Kaspersky): le serveur ne demarre alors pas.
4. Tuiles NetISO toujours visibles dans Aurora quand le PC est eteint.
