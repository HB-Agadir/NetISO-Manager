"""Interface texts in French, English and Arabic."""

LANGUAGES = {"fr": "Français", "en": "English", "ar": "العربية"}

_TEXTS = {
    # window
    "folders_frame": ("1. Dossiers contenant vos jeux (ISO ou dossiers de jeu)",
                      "1. Folders containing your games (ISOs or game folders)",
                      "1. المجلدات التي تحتوي على ألعابك (ملفات ISO أو مجلدات ألعاب)"),
    "add_folder": ("Ajouter un dossier...", "Add folder...", "إضافة مجلد..."),
    "remove": ("Retirer", "Remove", "إزالة"),
    "recursive": ("Inclure les sous-dossiers", "Include subfolders", "تضمين المجلدات الفرعية"),
    "refresh": ("Actualiser", "Refresh", "تحديث"),
    "auto_detect": ("Détecter les nouveaux jeux", "Detect new games", "اكتشاف الألعاب الجديدة"),
    "language": ("Langue", "Language", "اللغة"),
    "games_frame": ("2. Jeux détectés", "2. Detected games", "2. الألعاب المكتشفة"),
    "counts": ("{games} jeu(x)   ·   {isos} ISO   ·   {folders} dossier(s) de jeu",
               "{games} game(s)   ·   {isos} ISO   ·   {folders} game folder(s)",
               "{games} لعبة   ·   {isos} ISO   ·   {folders} مجلد ألعاب"),
    "counts_states": ("   ·   {netiso} en NetISO, {console} sur la console",
                      "   ·   {netiso} through NetISO, {console} on the console",
                      "   ·   {netiso} عبر NetISO، {console} على الجهاز"),
    "col_game": ("Jeu", "Game", "اللعبة"),
    "col_state": ("État", "Status", "الحالة"),
    "col_title": ("Title ID", "Title ID", "Title ID"),
    "col_disc": ("Disque", "Disc", "القرص"),
    "col_size": ("Taille", "Size", "الحجم"),
    "col_folder": ("Fichier", "File", "الملف"),
    "disc_of": ("{disc} sur {count}", "{disc} of {count}", "{disc} من {count}"),
    "next_disc": ("Changer de disque", "Switch disc", "تغيير القرص"),
    "group_discs": ("Une seule tuile par jeu multi-disques", "One tile per multi-disc game",
                    "اختصار واحد للعبة متعددة الأقراص"),
    "disc_selected": ("{name} : le disque {disc} sera lancé", "{name}: disc {disc} will be launched",
                      "{name}: سيتم تشغيل القرص {disc}"),
    "disc_in_use": ("{name} est en cours de jeu : le changement s'appliquera au prochain lancement.",
                    "{name} is being played: the change applies at the next launch.",
                    "{name} قيد اللعب: سيطبق التغيير عند التشغيل القادم."),
    "select_multi_disc": ("Sélectionnez un jeu qui a plusieurs disques.",
                          "Select a game that has several discs.",
                          "اختر لعبة تحتوي على عدة أقراص."),
    "now_playing": ("En cours", "Now playing", "قيد التشغيل"),
    "nothing_playing": ("aucun jeu", "no game", "لا توجد لعبة"),
    "playing_value": ("{name} (disque {disc}) · {rate:.1f} Mo/s",
                      "{name} (disc {disc}) · {rate:.1f} MB/s",
                      "{name} (القرص {disc}) · {rate:.1f} MB/s"),
    "start_with_windows": ("Démarrer avec Windows", "Start with Windows", "التشغيل مع Windows"),
    "setup_button": ("Installer le plugin sur la console", "Install the plugin on the console",
                     "تثبيت الإضافة على الجهاز"),
    "setup_confirm": (
        "Cette action configure la console pour NetISO :\n\n"
        "  1. envoie NetISO.xex s'il n'y est pas ;\n"
        "  2. écrit l'adresse de ce PC ({ip}) à côté du plugin ;\n"
        "  3. ajoute le plugin dans launch.ini si besoin, après en avoir fait une copie "
        "(launch.ini.netiso.bak).\n\nContinuer ?",
        "This sets the console up for NetISO:\n\n"
        "  1. uploads NetISO.xex if it is missing;\n"
        "  2. writes this PC's address ({ip}) next to the plugin;\n"
        "  3. adds the plugin to launch.ini if needed, after saving a copy "
        "(launch.ini.netiso.bak).\n\nContinue?",
        "سيتم إعداد الجهاز لـ NetISO:\n\n"
        "  1. إرسال NetISO.xex إذا لم يكن موجودا؛\n"
        "  2. كتابة عنوان هذا الحاسوب ({ip}) بجانب الإضافة؛\n"
        "  3. إضافة الإضافة إلى launch.ini عند الحاجة، بعد حفظ نسخة "
        "(launch.ini.netiso.bak).\n\nمتابعة؟"),
    "choose_plugin": ("Choisir le fichier NetISO.xex", "Choose the NetISO.xex file",
                      "اختر ملف NetISO.xex"),
    "setup_done_reboot": ("Console configurée. Redémarrez la console pour charger le plugin.",
                          "Console configured. Restart the console to load the plugin.",
                          "تم إعداد الجهاز. أعد تشغيل الجهاز لتحميل الإضافة."),
    "setup_done": ("Console configurée. Redémarrez-la si l'adresse du PC a changé.",
                   "Console configured. Restart it if the PC address has changed.",
                   "تم إعداد الجهاز. أعد تشغيله إذا تغير عنوان الحاسوب."),
    "setup_failed": ("Échec de la configuration : {error}", "Setup failed: {error}",
                     "فشل الإعداد: {error}"),
    "size_gb": ("{size:.1f} Go", "{size:.1f} GB", "{size:.1f} GB"),
    "state_netiso": ("Dans Aurora (NetISO)", "In Aurora (NetISO)", "في Aurora (NetISO)"),
    "state_console": ("Déjà sur la console", "Already on the console", "مثبتة على الجهاز"),
    "state_pending": ("À synchroniser", "Not synced yet", "بانتظار المزامنة"),
    "console_frame": ("3. Console", "3. Console", "3. الجهاز"),
    "console_ip": ("Adresse IP de la console", "Console IP address", "عنوان IP للجهاز"),
    "ftp_user": ("Utilisateur FTP", "FTP user", "مستخدم FTP"),
    "ftp_password": ("Mot de passe FTP", "FTP password", "كلمة مرور FTP"),
    "remote_root": ("Dossier des tuiles", "Tiles folder", "مجلد الاختصارات"),
    "console_folders": ("Jeux installés (dossiers)", "Installed games (folders)",
                        "الألعاب المثبتة (المجلدات)"),
    "sync_button": ("Synchroniser avec Aurora", "Sync with Aurora", "المزامنة مع Aurora"),
    "server_frame": ("4. Serveur", "4. Server", "4. الخادم"),
    "server_state": ("État", "Status", "الحالة"),
    "server_running": ("En marche, port {port}", "Running, port {port}", "يعمل، المنفذ {port}"),
    "server_stopped": ("Arrêté", "Stopped", "متوقف"),
    "pc_ip": ("Adresse de ce PC", "This PC's address", "عنوان هذا الحاسوب"),
    "pc_ip_unknown": ("inconnue", "unknown", "غير معروف"),
    "pc_ip_hint": ("(à mettre dans NetISO.xex.txt sur la console)",
                   "(put it in NetISO.xex.txt on the console)",
                   "(يوضع في ملف NetISO.xex.txt على الجهاز)"),
    "autostart": ("Démarrer le serveur à l'ouverture", "Start the server when the app opens",
                  "تشغيل الخادم عند فتح البرنامج"),
    "server_start": ("Démarrer le serveur", "Start server", "تشغيل الخادم"),
    "server_stop": ("Arrêter le serveur", "Stop server", "إيقاف الخادم"),
    "log_frame": ("Journal", "Log", "السجل"),
    "choose_folder": ("Choisir un dossier de jeux", "Choose a games folder", "اختر مجلد الألعاب"),
    "support_link": ("♥ Soutenir le projet", "♥ Support the project", "♥ ادعم المشروع"),
    "guide_link": ("Guide d'utilisation", "User guide", "دليل الاستخدام"),
    "welcome": (
        "Bienvenue dans NetISO Manager.\n\n"
        "Cette application est gratuite et le restera. Si elle vous est utile, vous pouvez "
        "soutenir son développement par un don, à tout moment, avec le lien « Soutenir le "
        "projet » en haut de la fenêtre.\n\nOuvrir la page de don maintenant ?",
        "Welcome to NetISO Manager.\n\n"
        "This application is free and will stay free. If you find it useful, you can support "
        "its development with a donation, at any time, with the \"Support the project\" link "
        "at the top of the window.\n\nOpen the donation page now?",
        "مرحبا بك في NetISO Manager.\n\n"
        "هذا البرنامج مجاني وسيبقى مجانيا. إذا كان مفيدا لك، يمكنك دعم تطويره بتبرع في أي وقت "
        "عبر رابط «ادعم المشروع» أعلى النافذة.\n\nهل تريد فتح صفحة التبرع الآن؟"),
    # dialogs
    "need_ip": ("Indiquez l'adresse IP de la console.", "Enter the console's IP address.",
                "أدخل عنوان IP للجهاز."),
    "no_games": ("Aucun jeu détecté. Ajoutez un dossier de jeux.",
                 "No game detected. Add a games folder.",
                 "لم يتم اكتشاف أي لعبة. أضف مجلد ألعاب."),
    "stub_missing": ("Lanceur introuvable : {error}", "Launcher not found: {error}",
                     "ملف التشغيل غير موجود: {error}"),
    "port_busy_dialog": (
        "Le port {port} est déjà utilisé par un autre programme (autre serveur NetISO ou "
        "antivirus). Fermez-le puis réessayez.",
        "Port {port} is already used by another program (another NetISO server or an "
        "antivirus). Close it and try again.",
        "المنفذ {port} مستخدم من برنامج آخر (خادم NetISO آخر أو مضاد فيروسات). أغلقه ثم "
        "حاول مجددا."),
    "changes_added": ("Nouveaux jeux détectés :", "New games detected:", "ألعاب جديدة:"),
    "changes_removed": ("Jeux retirés :", "Games removed:", "ألعاب محذوفة:"),
    "changes_more": ("... et {count} autre(s)", "... and {count} more", "... و{count} أخرى"),
    "changes_question": ("Voulez-vous les transférer vers Aurora maintenant ?",
                         "Do you want to transfer them to Aurora now?",
                         "هل تريد نقلها إلى Aurora الآن؟"),
    # log
    "scanning": ("Recherche des jeux dans {count} dossier(s)...",
                 "Looking for games in {count} folder(s)...",
                 "جاري البحث عن الألعاب في {count} مجلد..."),
    "games_found": ("{count} jeu(x) détecté(s)", "{count} game(s) detected",
                    "تم اكتشاف {count} لعبة"),
    "ignored": ("Ignoré : {path} ({reason})", "Skipped: {path} ({reason})",
                "تم التجاهل: {path} ({reason})"),
    "sync_start": ("Synchronisation de {count} jeu(x) avec {host}...",
                   "Syncing {count} game(s) with {host}...",
                   "جاري مزامنة {count} لعبة مع {host}..."),
    "sync_done": ("Terminé : {netiso} jeu(x) en NetISO, {console} déjà sur la console. "
                  "Lancez un scan dans Aurora.",
                  "Done: {netiso} game(s) through NetISO, {console} already on the console. "
                  "Run a scan in Aurora.",
                  "تم: {netiso} لعبة عبر NetISO، {console} مثبتة على الجهاز. قم بالفحص في Aurora."),
    "sync_failed": ("Échec de la synchronisation : {error}", "Sync failed: {error}",
                    "فشلت المزامنة: {error}"),
    "port_busy_retry": ("Port {port} occupé par un autre programme, nouvel essai...",
                        "Port {port} is used by another program, retrying...",
                        "المنفذ {port} مستخدم من برنامج آخر، إعادة المحاولة..."),
    "server_failed": ("Le serveur n'a pas pu démarrer : le port {port} est pris par un autre "
                      "programme (autre serveur NetISO ou antivirus).",
                      "The server could not start: port {port} is held by another program "
                      "(another NetISO server or an antivirus).",
                      "تعذر تشغيل الخادم: المنفذ {port} مستخدم من برنامج آخر (خادم NetISO آخر "
                      "أو مضاد فيروسات)."),
    # server
    "server_started": ("Serveur démarré sur le port {port}", "Server started on port {port}",
                       "تم تشغيل الخادم على المنفذ {port}"),
    "server_stopped_msg": ("Serveur arrêté", "Server stopped", "تم إيقاف الخادم"),
    "client_connected": ("Console connectée : {address}", "Console connected: {address}",
                         "تم اتصال الجهاز: {address}"),
    "client_disconnected": ("Console déconnectée : {address}", "Console disconnected: {address}",
                            "انقطع اتصال الجهاز: {address}"),
    "game_mounted": ("Jeu monté : {name} (disque {disc})", "Game mounted: {name} (disc {disc})",
                     "تم تحميل اللعبة: {name} (القرص {disc})"),
    "no_game_mounted": ("Aucun jeu monté", "No game mounted", "لا توجد لعبة محملة"),
    "unknown_game": ("Jeu inconnu demandé : {name}", "Unknown game requested: {name}",
                     "طلب لعبة غير معروفة: {name}"),
    "open_failed": ("Ouverture impossible : {path} ({error})", "Cannot open: {path} ({error})",
                    "تعذر فتح: {path} ({error})"),
    # console
    "ftp_connect_failed": ("connexion FTP impossible vers {host} ({error}). Aurora doit être "
                           "ouvert sur la console.",
                           "cannot connect to FTP on {host} ({error}). Aurora must be open on "
                           "the console.",
                           "تعذر الاتصال بـ FTP على {host} ({error}). يجب أن يكون Aurora مفتوحا "
                           "على الجهاز."),
    "looking_installed": ("Recherche des jeux déjà installés sur la console...",
                          "Looking for games already installed on the console...",
                          "جاري البحث عن الألعاب المثبتة على الجهاز..."),
    "installed_count": ("{count} jeu(x) installé(s) sur la console",
                        "{count} game(s) installed on the console",
                        "{count} لعبة مثبتة على الجهاز"),
    "tile_removed": ("Tuile retirée : {name}", "Tile removed: {name}", "تم حذف الاختصار: {name}"),
    "mkdir_refused": ("création de {path} refusée ({error})", "cannot create {path} ({error})",
                      "تعذر إنشاء {path} ({error})"),
    "verify_failed": ("{path} est différent sur la console après l'envoi",
                      "{path} differs on the console after upload",
                      "الملف {path} مختلف على الجهاز بعد الإرسال"),
    "ftp_error": ("erreur FTP : {error}", "FTP error: {error}", "خطأ FTP: {error}"),
    "console_no_server": ("NetISO : PC injoignable. Ouvrez NetISO Manager.",
                          "NetISO: PC not reachable. Open NetISO Manager.",
                          "NetISO: تعذر الوصول إلى الحاسوب. افتح NetISO Manager."),
    "unknown_device": ("emplacement inconnu dans launch.ini : {path}",
                       "unknown location in launch.ini: {path}",
                       "موقع غير معروف في launch.ini: {path}"),
    "no_plugin_slot": ("aucun emplacement de plugin libre dans launch.ini",
                       "no free plugin slot in launch.ini",
                       "لا توجد خانة إضافة فارغة في launch.ini"),
    "no_launch_ini": ("launch.ini introuvable sur la console", "launch.ini not found on the console",
                      "الملف launch.ini غير موجود على الجهاز"),
    "plugin_missing": ("NetISO.xex absent de la console ({path})",
                       "NetISO.xex is not on the console ({path})",
                       "الملف NetISO.xex غير موجود على الجهاز ({path})"),
    "plugin_uploaded": ("Plugin envoyé : {path}", "Plugin uploaded: {path}",
                        "تم إرسال الإضافة: {path}"),
    "address_written": ("Adresse du PC {ip} écrite dans {path}", "PC address {ip} written to {path}",
                        "تمت كتابة عنوان الحاسوب {ip} في {path}"),
    "ini_updated": ("{path} mis à jour (copie : launch.ini.netiso.bak)",
                    "{path} updated (backup: launch.ini.netiso.bak)",
                    "تم تحديث {path} (نسخة احتياطية: launch.ini.netiso.bak)"),
    "bad_tiles_folder": ("dossier des tuiles invalide : {path}. Indiquez un dossier dédié, par "
                         "exemple /Hdd1/NetISO.",
                         "invalid tiles folder: {path}. Use a dedicated folder such as /Hdd1/NetISO.",
                         "مجلد الاختصارات غير صالح: {path}. استخدم مجلدا خاصا مثل /Hdd1/NetISO."),
    "backup_saved": ("Copie de sécurité de la liste d'Aurora enregistrée : {path}",
                     "Safety copy of Aurora's list saved: {path}",
                     "تم حفظ نسخة احتياطية من قائمة Aurora: {path}"),
    "cleanup_description": ("Retire de la liste d'Aurora les tuiles NetISO qui n'existent plus",
                            "Removes NetISO tiles that no longer exist from Aurora's list",
                            "Removes NetISO tiles that no longer exist from Aurora's list"),
    "cleanup_question": ("Retirer {count} ancienne(s) entree(s) NetISO de la liste ? Vos jeux ne sont pas touches.",
                         "Remove {count} old NetISO entries from the list? Your games are not touched.",
                         "Remove {count} old NetISO entries from the list? Your games are not touched."),
    "cleanup_done": ("Termine. La liste va se rafraichir.", "Done. The list will refresh.",
                     "Done. The list will refresh."),
    "cleanup_ready": (
        "Aurora affiche encore {count} ancienne(s) tuile(s). Pour les retirer : dans Aurora, "
        "ouvrez les scripts utilitaires et lancez « NetISO Cleanup ».",
        "Aurora still shows {count} old tile(s). To remove them: in Aurora, open the utility "
        "scripts and run \"NetISO Cleanup\".",
        "ما زال Aurora يعرض {count} اختصارا قديما. لإزالتها: افتح سكربتات الأدوات في Aurora وشغل "
        "«NetISO Cleanup»."),
    # ISO reading
    "no_partition": ("partition de jeu introuvable", "game partition not found",
                     "لم يتم العثور على قسم اللعبة"),
    "file_missing": ("{name} absent de la racine du disque", "{name} missing from the disc root",
                     "الملف {name} غير موجود في جذر القرص"),
    "not_xex2": ("default.xex n'est pas un fichier XEX2", "default.xex is not an XEX2 file",
                 "الملف default.xex ليس بصيغة XEX2"),
    "no_exec_info": ("default.xex sans en-tête d'exécution", "default.xex has no execution info",
                     "الملف default.xex لا يحتوي على معلومات التشغيل"),
    "bad_stub": ("lanceur inattendu : empreinte d'en-tête non reconnue",
                 "unexpected launcher: header hash not recognised",
                 "ملف تشغيل غير متوقع: بصمة الترويسة غير معروفة"),
}

_ORDER = ("fr", "en", "ar")
_current = "en"


def set_language(code):
    global _current
    _current = code if code in LANGUAGES else "en"


def language():
    return _current


def tr(key, **values):
    text = _TEXTS[key][_ORDER.index(_current)]
    return text.format(**values) if values else text
