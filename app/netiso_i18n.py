"""Interface texts in French, English and Arabic."""

LANGUAGES = {"fr": "Français", "en": "English", "ar": "العربية"}

_TEXTS = {
    # window
    "folders_frame": ("1. Dossiers contenant vos ISO", "1. Folders containing your ISOs",
                      "1. المجلدات التي تحتوي على ملفات ISO"),
    "add_folder": ("Ajouter un dossier...", "Add folder...", "إضافة مجلد..."),
    "remove": ("Retirer", "Remove", "إزالة"),
    "recursive": ("Inclure les sous-dossiers", "Include subfolders", "تضمين المجلدات الفرعية"),
    "refresh": ("Actualiser", "Refresh", "تحديث"),
    "auto_detect": ("Détecter les nouveaux ISO", "Detect new ISOs", "اكتشاف ملفات ISO الجديدة"),
    "language": ("Langue", "Language", "اللغة"),
    "games_frame": ("2. Jeux détectés", "2. Detected games", "2. الألعاب المكتشفة"),
    "col_game": ("Jeu", "Game", "اللعبة"),
    "col_state": ("État", "Status", "الحالة"),
    "col_title": ("Title ID", "Title ID", "Title ID"),
    "col_disc": ("Disque", "Disc", "القرص"),
    "col_size": ("Taille", "Size", "الحجم"),
    "col_folder": ("Dossier", "Folder", "المجلد"),
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
    "choose_folder": ("Choisir un dossier d'ISO", "Choose an ISO folder", "اختر مجلد ملفات ISO"),
    # dialogs
    "need_ip": ("Indiquez l'adresse IP de la console.", "Enter the console's IP address.",
                "أدخل عنوان IP للجهاز."),
    "no_games": ("Aucun jeu détecté. Ajoutez un dossier d'ISO.",
                 "No game detected. Add an ISO folder.",
                 "لم يتم اكتشاف أي لعبة. أضف مجلد ملفات ISO."),
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
    "scanning": ("Recherche des ISO dans {count} dossier(s)...",
                 "Looking for ISOs in {count} folder(s)...",
                 "جاري البحث عن ملفات ISO في {count} مجلد..."),
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
    "game_mounted": ("Jeu monté : {name}", "Game mounted: {name}", "تم تحميل اللعبة: {name}"),
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
_current = "fr"


def set_language(code):
    global _current
    _current = code if code in LANGUAGES else "fr"


def language():
    return _current


def tr(key, **values):
    text = _TEXTS[key][_ORDER.index(_current)]
    return text.format(**values) if values else text
