# Changelog

## 1.3.0

Everything below is new since 1.2.0. It was tested on a real console (RGH, Aurora 0.7b.2).

### Aurora shows only the games you can play

- **"Available games" view.** Each sync installs small scripts in Aurora. Run **"NetISO Setup"** once from Aurora's utility scripts, and Aurora opens on a view where:
  - the games played from the PC are hidden while NetISO Manager's server is not running, and come back when it runs;
  - installation discs and voice packs, which are not games, are hidden (for example the Resident Evil 6 voice pack, which Aurora lists as "RESIDENT EVIL 6" while the game itself is "BIOHAZARD 6"). Every game disc stays visible: Battlefield 4 starts its campaign from disc 2.
- **The list follows the server.** Aurora only applies its filters when it builds its list, so NetISO Manager restarts Aurora when the server starts or stops. Only when Aurora is on screen, never during a game.
- **"NetISO" subtitle** (optional, chosen in Aurora): under each game, "On the console", "Played from the PC" or "PC off: start NetISO Manager".
- How it works: while its server runs, the app keeps a small file, `pc_online.txt`, in the tiles folder on the console, and deletes it when the server stops. After a crash or a power cut the file stays, the PC games stay visible, and the console's "PC not reachable" message remains the safety net.

### Multi-disc games

- A tile now starts on the **game disc**, not on an installation or voice disc. Watch_Dogs starts on disc 2 (the game) instead of disc 1 (the installation). The installation disc stays one trigger pull away.
- The game list shows each disc's role, for example "1 of 2 (install)" or "2 of 2 (add-on)".

### Setting up and fixing problems

- **"Test my setup"** checks, in one click: the PC's server, the Windows network type, the console's address, the FTP login, `launch.ini`, the plugin version, the PC address the plugin uses, and Aurora's web server. Every problem comes with what to do.
- **"Copy a diagnostic report"** prepares a text to paste in a forum post or an issue. It holds no password, no full address and no user name.
- **"Find" button** next to the console's address: looks for the console on the local network and fills in its address.
- **The PC's address is followed.** When the router gives the PC a new address (often after it restarts), the console kept asking the old one and every game failed. The app now checks at start-up, every 5 minutes and at each sync, writes the new address on the console, and asks you to restart the console.
- **Windows "Public" network detected.** When Windows files the network as Public, its firewall blocks the console. The app now says so and offers to set it to Private, through Windows' own administrator prompt. It never changes it without your answer.
- **Incomplete ISOs reported.** Every ISO is checked: a file shorter than its disc (interrupted download or copy) is reported instead of crashing on the console. A file is checked once per version, so start-up stays fast.

### Playing

- **The PC stays awake** while the console reads a game: a PC that went to sleep made the game crash. Ten minutes after the last read, Windows may sleep again as usual.
- **"Play on this PC (Xenia)"** starts the selected game in the Xenia emulator, which you install yourself. Not every game runs in Xenia.

### Fixes

- The console's **"PC not reachable" message now stays on screen**. The launcher used to go back to Aurora at once and the message was lost, which looked like a crash.
- The message for a refused Aurora web login now reminds the factory login (`xboxhttp` / `xboxhttp`).

### Other changes

- **Application icon**, in the windows, on the shortcuts and in Windows' installed apps.
- **Version number in the window title.**
- **New version notice**: once per version, the app tells you when a newer release is out. This request to GitHub at start-up is the app's only Internet access; nothing about you is sent.
- **Portable zip** next to the installer, for people who would rather not install. Without the installer, Windows asks about the firewall the first time the server starts.
- **User guides** (English and French) updated: the "Available games" view, Xenia, and new troubleshooting entries ("PC not reachable", Public network, installed games stuck on their loading screen).

### Under the hood

Ready and tested, with screens to come in a later version:

- Console storage: the drives plugged in, and their free space.
- Copies to and from the console checked with a CRC32 computed on the console itself.
- Installed games sorted by how long ago they were last played.
- Game covers, as JPEG and PNG, from the addresses Aurora keeps.
- Launching a game on the console from the PC.
- Installing title updates and DLC from the PC to the right console folder.
- Extracting an ISO to a game folder.

### Known limits

- After a power cut or a crash of the PC, the PC games stay visible in Aurora until NetISO Manager runs again.
- Changing discs still means going back to Aurora and launching the tile again (right trigger for the next disc).
- Installed games: Aurora's list does not group the discs of one game. Since every game disc stays visible, a two-disc game installed on the console shows twice.

## 1.2.0

- The NetISO.xex plugin by cOz ships with the installer (unmodified) and is installed on the console by one button.
- Fast loading: about twice as fast (8.9 MB/s measured against 4.1 MB/s).
- See the console's screen on the PC while setting things up.
- Extracted game folders work next to ISO files.
- The game list shows how many games, ISOs and game folders were found.

Earlier versions: see the [releases page](https://github.com/HB-Agadir/NetISO-Manager/releases).
