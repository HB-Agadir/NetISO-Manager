# NetISO Manager

<img src="icon.png" alt="NetISO Manager" width="128">

English | [Francais](README.fr.md)

Play the Xbox 360 ISOs stored on your Windows PC straight from the Aurora game list, on an RGH/JTAG console.

**Free and open source.** If you find it useful, you can support its development: **[ko-fi.com/x360remap](https://ko-fi.com/x360remap)**

Every ISO on the PC shows up in Aurora like an installed game, with its cover and title. Press A and the ISO is mounted over the network and the game starts. The Guide button and going back to Aurora work as usual.

## What it does

- Pick one or more game folders, on any drive of the PC, subfolders included.
- Works with ISO files and with extracted game folders (a folder holding `default.xex`). A folder is presented to the console as a disc on the fly: nothing is converted or copied, and it streams at the same speed as an ISO.
- Reads the Title ID and Media ID from each ISO (XGD2, XGD3, XISO).
- Builds one tile per game and sends it to the console over Aurora's FTP server, checking every file after upload.
- Built-in NetISO server that serves the games of all folders at once.
- Automatic detection: when an ISO is added to or removed from a folder, the app tells you and offers to transfer it to Aurora.
- One tile per game, even when it spans several discs. Pick the disc from the console by holding the right trigger (next disc) or the left trigger (previous disc) as the tile starts, or pick it in the app. You can also keep one tile per disc if you prefer.
- No duplicates: a game already installed on the console keeps priority and gets no tile. Delete it from the console and its NetISO tile comes back at the next sync.
- Cleans up the entries Aurora keeps for tiles that are gone, without touching your games.
- One-click plugin setup on the console (PC address and `launch.ini`, with a backup).
- Fast loading: about twice the read speed of the stock NetISO setup (8.9 MB/s measured against 4.1).
- Shows the console's screen in a window on the PC, so you can follow the setup without switching HDMI inputs.
- Shows the game being played and the transfer rate; can start with Windows.
- Interface in English, French and Arabic.

## Download

Get `NetISOManager-x64.msi` from the [releases page](https://github.com/HB-Agadir/NetISO-Manager/releases). It installs the app, the console launcher and the user guide. Windows may show an "unknown publisher" warning because the installer is not signed: click "More info", then "Run anyway".

The user guide opens from the link at the top of the app. It is also in [docs/Guide_en.html](docs/Guide_en.html) and [docs/Guide_fr.html](docs/Guide_fr.html).

## Requirements

- An RGH or JTAG Xbox 360 with DashLaunch and Aurora 0.7b.
- The `NetISO.xex` 1.0 plugin by cOz. It ships with NetISO Manager, unmodified, and is installed by the setup button.
- A 64-bit Windows PC on the same network as the console, preferably wired. Running from source needs Python 3 with Tkinter.
- Your own ISOs or game folders, from games you own.

## Quick start

1. Install and open NetISO Manager.
2. Add the folders that hold your games.
3. Enter the console's IP address, with Aurora open on the console.
4. Click "Install the plugin on the console" and restart the console. This is done once.
5. Click "Sync with Aurora".
6. In Aurora, add `Hdd1:\NetISO` to the game scan paths with a depth of at least 2, then run a scan. This is done once.
7. Launch a game.

Keep the app open while you play: it is the one serving the ISOs. With the PC off, games installed on the console still work; NetISO tiles stay visible but do not launch.

The modified Nova.xex of the classic NetISO method is not needed.

### Setting the console up by hand

If you would rather not use the setup button: copy `app/plugin/NetISO.xex` to the console (for example `Hdd1:\Apps\`), create `NetISO.xex.txt` next to it holding only the PC's IP address, and add the plugin to a free slot of the `[Plugins]` section of `launch.ini`:

```
plugin4 = Hdd:\Apps\NetISO.xex
```

## How it works

The `NetISO.xex` plugin can present a remote ISO as a disc in the drive, but you have to go through the file manager to choose the game. NetISO Manager replaces that step:

- each tile is a small launcher (`stub/`) carrying the game's Title ID, which lets Aurora identify it;
- when launched, it asks the plugin to mount its ISO, waits for the disc to be readable, then boots the game;
- the built-in server (`app/netiso_server.py`) speaks the protocol of the original NetISO server.

Technical details, including the obstacles met along the way, are in [docs/NOTES_TECHNIQUES.md](docs/NOTES_TECHNIQUES.md) (in French).

## Known limits

- TCP port 4323 is fixed by the plugin. If another program holds it (an antivirus, for instance), the server cannot start.
- Speed is capped by the console's 100 Mbit/s Ethernet port. Fast loading reaches about 8.9 MB/s.
- The console screen window shows one image about every three seconds. It is a setup aid, not a video stream.
- The launcher only acts on version 1.0 of the plugin. With another version it changes nothing, and the Guide button may then stay dead after a launch.
- The disc of a multi-disc game is chosen when the tile starts. Switching disc without leaving the game is not possible.
- Whether title updates apply to games launched through NetISO has not been checked yet.
- Tested on a single console: Trinity, dashboard 17559, Aurora 0.7b.2.

## Building

`app/stub.xex` ships prebuilt. To rebuild the launcher: Visual Studio with the Xbox 360 SDK, configuration `Release Retail | Xbox 360`, and the xkelib library. Adjust the path to xkelib in `stub/stub.vcxproj` (property `XkelibDir`).

`build_msi.bat` creates `dist\NetISOManager-<version>-x64.msi` with PyInstaller and WiX 5. The installer puts the app in `Program Files`, creates the shortcuts (app and guides), and adds a firewall rule limited to this program, TCP port 4323, private networks and the local subnet. `build_exe.bat` produces a single portable executable instead.

## Tests

```
python app/tests/test_core.py
python app/tests/test_app.py
python app/tests/test_cleanup.py
python app/tests/test_folders.py
python app/tests/test_nova.py
```

## Support the project

NetISO Manager is free and will stay free. If you find it useful, you can support its development with a donation:

**[ko-fi.com/x360remap](https://ko-fi.com/x360remap)**

The link is also in the app ("Support the project", at the top of the window) and in the user guide. By the same author: [X360Remap](https://github.com/HB-Agadir/X360Remap).

## Thanks

NetISO Manager only makes other people's work easier to use. It would not exist without them.

- **cOz**, author of the NetISO plugin and of DashLaunch. His plugin is what makes the console believe a disc is in the drive: everything else rests on it. Thanks also to those he thanks himself in his original readme: SpkLeader, Swizzy, Phoenix, vgcrepairs, Team Xecuter, RF1911 and tydye.
- **ConfusionRS**, for the NetISO package adapted to Aurora 0.7b, which made this method known and working on today's consoles.
- **tuxuser**, for `netiso-srv`, the open server whose code served as the reference for the protocol.
- **muradbu**, for the `netiso` project, which showed the idea of one launcher per game recognised by Aurora.
- **Team Phoenix**, for Aurora and its script system, used here to clean up the game list.
- **Warranty Voider (zeroKilo)** and **SaveEditors**, for XEXLoaderWV, and the **Ghidra** team: the tools that made it possible to understand how to talk to the plugin.
- The authors of **xkelib**, used to build the launcher.
- The **ConsoleMods** community, for its documentation.

NetISO Manager is not affiliated with any of them.

**About the bundled plugin.** `app/plugin/NetISO.xex` is cOz's NetISO 1.0, included exactly as he released it, together with his original readme (`app/plugin/NetISO-README-cOz.txt`). It is bundled for one reason: the launcher only works with this exact build, and asking newcomers to find the right file elsewhere was the main obstacle to getting started. It remains entirely his work. If cOz or anyone holding rights to it would rather it not be distributed here, open an issue and it will be removed.

## License

NetISO Manager is released under the GNU GPL version 3: see the `LICENSE` file. You may use, modify and redistribute it, provided you keep this license and publish your source.
