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
    "role_install": ("installation", "install", "تثبيت"),
    "role_extra": ("contenu", "add-on", "محتوى"),
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
    "fast_read": ("Chargements rapides (environ 2 fois plus vite)", "Fast loading (about twice as fast)",
                  "تحميل سريع (أسرع بمرتين تقريبا)"),
    "start_with_windows": ("Démarrer avec Windows", "Start with Windows", "التشغيل مع Windows"),
    "view_button": ("Voir l'écran de la console", "Show the console's screen", "عرض شاشة الجهاز"),
    "view_title": ("Écran de la console", "Console screen", "شاشة الجهاز"),
    "view_connecting": ("Connexion à la console...", "Connecting to the console...",
                        "جاري الاتصال بالجهاز..."),
    "view_status": ("{title}   ·   une image toutes les {seconds:.0f} s environ",
                    "{title}   ·   one image about every {seconds:.0f} s",
                    "{title}   ·   صورة كل {seconds:.0f} ثانية تقريبا"),
    "view_in_aurora": ("Dans Aurora", "In Aurora", "في Aurora"),
    "view_in_game": ("En jeu (Title ID {titleid})", "In game (Title ID {titleid})",
                     "في لعبة (Title ID {titleid})"),
    "view_unauthorized": (
        "La console refuse l'utilisateur ou le mot de passe web d'Aurora. Vérifiez-les dans la "
        "zone Console (réglages d'Aurora, serveur HTTP). Ceux d'origine sont xboxhttp / xboxhttp : "
        "laissez les deux champs vides pour les utiliser.",
        "The console rejects Aurora's web user or password. Check them in the Console area "
        "(Aurora settings, HTTP server). The factory ones are xboxhttp / xboxhttp: leave both "
        "fields empty to use them.",
        "الجهاز يرفض مستخدم أو كلمة مرور ويب Aurora. تحقق منهما في منطقة الجهاز "
        "(إعدادات Aurora، خادم HTTP). بيانات المصنع هي xboxhttp / xboxhttp: اترك الحقلين فارغين "
        "لاستعمالها."),
    "test_button": ("Tester ma configuration", "Test my setup", "اختبار الإعدادات"),
    "report_button": ("Copier un rapport de diagnostic", "Copy a diagnostic report",
                      "نسخ تقرير التشخيص"),
    "find_button": ("Chercher", "Find", "بحث"),
    "xenia_button": ("Jouer sur ce PC (Xenia)", "Play on this PC (Xenia)",
                     "اللعب على هذا الحاسوب (Xenia)"),
    "check_title": ("Test de la configuration", "Setup test", "اختبار الإعدادات"),
    "check_running": ("Test en cours...", "Testing...", "جاري الاختبار..."),
    "check_done": ("Test terminé : {ok} bon(s), {warn} avertissement(s), {fail} problème(s).",
                   "Test finished: {ok} fine, {warn} warning(s), {fail} problem(s).",
                   "انتهى الاختبار: {ok} سليم، {warn} تنبيه، {fail} مشكلة."),
    "check_server_ok": ("Le serveur du PC est démarré.", "The PC's server is running.",
                        "خادم الحاسوب يعمل."),
    "check_server_off": ("Le serveur du PC est arrêté : cliquez sur « Démarrer le serveur ».",
                         "The PC's server is stopped: click \"Start server\".",
                         "خادم الحاسوب متوقف: اضغط «تشغيل الخادم»."),
    "check_network_ok": ("Réseau Windows de type {category} : le pare-feu laisse passer la console.",
                         "Windows network type {category}: the firewall lets the console in.",
                         "نوع شبكة Windows {category}: الجدار الناري يسمح للجهاز."),
    "check_network_public": (
        "Windows classe ce réseau comme Public : son pare-feu bloque la console. Paramètres > "
        "Réseau et Internet > Ethernet (ou Wi-Fi) > Type de profil réseau > Privé.",
        "Windows treats this network as Public: its firewall blocks the console. Settings > "
        "Network & internet > Ethernet (or Wi-Fi) > Network profile type > Private.",
        "يعتبر Windows هذه الشبكة عامة: الجدار الناري يحجب الجهاز. الإعدادات > الشبكة والإنترنت > "
        "Ethernet (أو Wi-Fi) > نوع ملف تعريف الشبكة > خاصة."),
    "check_network_unknown": ("Type de réseau Windows inconnu (impossible à lire).",
                              "Windows network type unknown (could not be read).",
                              "نوع شبكة Windows غير معروف (تعذرت قراءته)."),
    "check_no_console_ip": ("Aucune adresse de console : tapez-la ou cliquez sur « Chercher ».",
                            "No console address: type it or click \"Find\".",
                            "لا يوجد عنوان للجهاز: اكتبه أو اضغط «بحث»."),
    "check_console_unreachable": (
        "La console {host} ne répond pas. Elle doit être allumée sur Aurora, sur le même réseau. "
        "Son adresse a peut-être changé : cliquez sur « Chercher ».",
        "The console {host} does not answer. It must be on, in Aurora, on the same network. "
        "Its address may have changed: click \"Find\".",
        "الجهاز {host} لا يجيب. يجب أن يكون مشغلا على Aurora وعلى نفس الشبكة. ربما تغير عنوانه: "
        "اضغط «بحث»."),
    "check_ftp_login": ("La console refuse l'utilisateur ou le mot de passe FTP.",
                        "The console rejects the FTP user or password.",
                        "الجهاز يرفض مستخدم أو كلمة مرور FTP."),
    "check_console_ok": ("Console {host} joignable, connexion FTP acceptée.",
                         "Console {host} reachable, FTP login accepted.",
                         "الجهاز {host} متاح، تم قبول دخول FTP."),
    "check_no_launch_ini": ("Pas de launch.ini sur la console : DashLaunch est-il installé ?",
                            "No launch.ini on the console: is DashLaunch installed?",
                            "لا يوجد launch.ini على الجهاز: هل DashLaunch مثبت؟"),
    "check_no_plugin_slot": ("launch.ini n'a plus de place pour un plugin.",
                             "launch.ini has no free plugin slot.",
                             "لا توجد خانة إضافة فارغة في launch.ini."),
    "check_plugin_not_loaded": ("{path} ne charge pas NetISO.xex : cliquez sur « Installer le plugin ».",
                                "{path} does not load NetISO.xex: click \"Install the plugin\".",
                                "{path} لا يحمل NetISO.xex: اضغط «تثبيت الإضافة»."),
    "check_plugin_missing": ("Le plugin {path} n'est pas sur la console : cliquez sur « Installer le plugin ».",
                             "The plugin {path} is not on the console: click \"Install the plugin\".",
                             "الإضافة {path} غير موجودة على الجهاز: اضغط «تثبيت الإضافة»."),
    "check_plugin_ok": ("Plugin {path} présent, version d'origine de cOz.",
                        "Plugin {path} present, cOz's original version.",
                        "الإضافة {path} موجودة، النسخة الأصلية من cOz."),
    "check_plugin_other": (
        "Le plugin {path} n'est pas la version fournie : le bouton Guide et le chargement rapide "
        "peuvent ne pas marcher.",
        "The plugin {path} is not the version shipped with the app: the Guide button and fast "
        "loading may not work.",
        "الإضافة {path} ليست النسخة المرفقة: قد لا يعمل زر Guide والتحميل السريع."),
    "check_address_missing": ("Le plugin ne connaît pas l'adresse du PC : cliquez sur « Installer le plugin ».",
                              "The plugin does not know the PC's address: click \"Install the plugin\".",
                              "الإضافة لا تعرف عنوان الحاسوب: اضغط «تثبيت الإضافة»."),
    "check_address_wrong": (
        "Le plugin cherche le PC à {found}, mais le PC est à {ip}. NetISO Manager le corrige "
        "tout seul en quelques minutes, ou cliquez sur « Installer le plugin ». Puis redémarrez la console.",
        "The plugin looks for the PC at {found}, but the PC is at {ip}. NetISO Manager fixes it "
        "on its own within minutes, or click \"Install the plugin\". Then restart the console.",
        "الإضافة تبحث عن الحاسوب في {found} بينما عنوانه {ip}. سيصححه NetISO Manager خلال دقائق، "
        "أو اضغط «تثبيت الإضافة». ثم أعد تشغيل الجهاز."),
    "check_address_ok": ("Le plugin cherche bien le PC à {ip}.", "The plugin looks for the PC at {ip}, as it should.",
                         "الإضافة تبحث عن الحاسوب في {ip} كما يجب."),
    "check_ftp_error": ("Erreur FTP : {error}", "FTP error: {error}", "خطأ FTP: {error}"),
    "check_web_ok": ("Serveur web d'Aurora accessible (écran de la console disponible).",
                     "Aurora's web server reachable (console screen available).",
                     "خادم ويب Aurora متاح (شاشة الجهاز متوفرة)."),
    "check_web_failed": (
        "Serveur web d'Aurora injoignable ou identifiants refusés : seule la fenêtre « écran de "
        "la console » en dépend.",
        "Aurora's web server not reachable or login refused: only the console screen window "
        "needs it.",
        "خادم ويب Aurora غير متاح أو رُفض الدخول: نافذة شاشة الجهاز وحدها تحتاجه."),
    "report_copied": (
        "Rapport copié dans le presse-papiers. Il ne contient ni mot de passe, ni adresse "
        "complète, ni nom d'utilisateur : collez-le dans votre message.",
        "Report copied to the clipboard. It holds no password, no full address and no user "
        "name: paste it in your message.",
        "تم نسخ التقرير. لا يحتوي على كلمات مرور ولا عناوين كاملة ولا اسم مستخدم: الصقه في رسالتك."),
    "find_running": ("Recherche de la console sur le réseau...", "Looking for the console on the network...",
                     "جاري البحث عن الجهاز في الشبكة..."),
    "find_none": (
        "Aucune console trouvée. Elle doit être allumée sur Aurora, avec son serveur FTP actif, "
        "sur le même réseau que ce PC.",
        "No console found. It must be on, in Aurora, with its FTP server enabled, on the same "
        "network as this PC.",
        "لم يتم العثور على أي جهاز. يجب أن يكون مشغلا على Aurora مع تفعيل خادم FTP وعلى نفس شبكة "
        "هذا الحاسوب."),
    "find_found": ("Console trouvée : {host}", "Console found: {host}", "تم العثور على الجهاز: {host}"),
    "find_others": ("Autres appareils possibles : {hosts}", "Other possible devices: {hosts}",
                    "أجهزة محتملة أخرى: {hosts}"),
    "xenia_no_game": ("Sélectionnez d'abord un jeu dans la liste.", "Select a game in the list first.",
                      "اختر لعبة من القائمة أولا."),
    "xenia_pick": ("Où est xenia_canary.exe ?", "Where is xenia_canary.exe?", "أين يوجد xenia_canary.exe؟"),
    "xenia_started": ("Xenia lancé : {name}. Tous les jeux ne fonctionnent pas dans Xenia.",
                      "Xenia started: {name}. Not every game runs in Xenia.",
                      "تم تشغيل Xenia: {name}. ليست كل الألعاب تعمل في Xenia."),
    "xenia_failed": ("Impossible de lancer Xenia : {error}", "Could not start Xenia: {error}",
                     "تعذر تشغيل Xenia: {error}"),
    "xenia_no_target": ("fichier introuvable : {path}", "file not found: {path}", "الملف غير موجود: {path}"),
    "update_available": (
        "Une nouvelle version de NetISO Manager est disponible : {tag} (vous avez {current}).\n\n"
        "Ouvrir la page de téléchargement ?",
        "A new version of NetISO Manager is available: {tag} (you have {current}).\n\n"
        "Open the download page?",
        "يتوفر إصدار جديد من NetISO Manager: {tag} (لديك {current}).\n\nفتح صفحة التنزيل؟"),
    "awake_on": ("Partie en cours : le PC ne se mettra pas en veille.",
                 "Game in progress: the PC will not go to sleep.",
                 "لعبة جارية: لن يدخل الحاسوب في وضع السكون."),
    "awake_off": ("Plus de lecture depuis 10 minutes : le PC peut de nouveau se mettre en veille.",
                  "No reads for 10 minutes: the PC may sleep again.",
                  "لا قراءة منذ 10 دقائق: يمكن للحاسوب الدخول في السكون من جديد."),
    "view_unreachable": (
        "Console injoignable ({error}). Elle doit être allumée, avec le serveur HTTP activé dans "
        "les réglages d'Aurora. Nouvel essai...",
        "Console not reachable ({error}). It must be on, with the HTTP server enabled in "
        "Aurora's settings. Retrying...",
        "تعذر الوصول إلى الجهاز ({error}). يجب أن يكون مشغلا مع تفعيل خادم HTTP في إعدادات "
        "Aurora. إعادة المحاولة..."),
    "setup_button": ("Installer le plugin sur la console", "Install the plugin on the console",
                     "تثبيت الإضافة على الجهاز"),
    "setup_confirm": (
        "Cette action configure la console pour NetISO :\n\n"
        "  1. installe le plugin NetISO.xex de cOz, fourni avec ce logiciel, s'il n'y est pas ;\n"
        "  2. écrit l'adresse de ce PC ({ip}) à côté du plugin ;\n"
        "  3. ajoute le plugin dans launch.ini si besoin, après en avoir fait une copie "
        "(launch.ini.netiso.bak).\n\nContinuer ?",
        "This sets the console up for NetISO:\n\n"
        "  1. installs cOz's NetISO.xex plugin, shipped with this software, if it is missing;\n"
        "  2. writes this PC's address ({ip}) next to the plugin;\n"
        "  3. adds the plugin to launch.ini if needed, after saving a copy "
        "(launch.ini.netiso.bak).\n\nContinue?",
        "سيتم إعداد الجهاز لـ NetISO:\n\n"
        "  1. تثبيت إضافة NetISO.xex من cOz المرفقة مع البرنامج إذا لم تكن موجودة؛\n"
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
    "http_user": ("Utilisateur web d'Aurora", "Aurora web user", "مستخدم ويب Aurora"),
    "http_password": ("Mot de passe web d'Aurora", "Aurora web password", "كلمة مرور ويب Aurora"),
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
    "not_a_package": ("{path} n'est ni une mise à jour de jeu ni un DLC",
                      "{path} is neither a title update nor a DLC",
                      "{path} ليس تحديثا للعبة ولا محتوى إضافيا"),
    "aurora_db_missing": ("Base d'Aurora illisible : Aurora doit être ouvert sur la console.",
                          "Aurora's database cannot be read: Aurora must be open on the console.",
                          "تعذرت قراءة قاعدة Aurora: يجب أن يكون Aurora مفتوحا على الجهاز."),
    "launch_drive_unsupported": ("Lancement à distance impossible depuis le disque {drive}.",
                                 "Remote launch is not possible from drive {drive}.",
                                 "التشغيل عن بعد غير ممكن من القرص {drive}."),
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
    "plugin_other_version": (
        "Attention : {path} n'est pas la version 1.0 de NetISO.xex fournie avec NetISO Manager. "
        "Les jeux se lanceront, mais le bouton Guide et les chargements rapides peuvent ne pas "
        "fonctionner. Supprimez ce fichier de la console puis relancez l'installation.",
        "Warning: {path} is not the NetISO.xex 1.0 shipped with NetISO Manager. Games will "
        "launch, but the Guide button and fast loading may not work. Delete that file from the "
        "console, then run the installation again.",
        "تنبيه: {path} ليس نسخة NetISO.xex 1.0 المرفقة مع NetISO Manager. ستعمل الألعاب، لكن زر "
        "Guide والتحميل السريع قد لا يعملان. احذف هذا الملف من الجهاز ثم أعد التثبيت."),
    "plugin_uploaded": ("Plugin envoyé : {path}", "Plugin uploaded: {path}",
                        "تم إرسال الإضافة: {path}"),
    "address_written": ("Adresse du PC {ip} écrite dans {path}", "PC address {ip} written to {path}",
                        "تمت كتابة عنوان الحاسوب {ip} في {path}"),
    "address_fixed_log": (
        "L'adresse du PC a changé ({old} -> {ip}) : {path} corrigé. Redémarrez la console.",
        "The PC's address changed ({old} -> {ip}): {path} corrected. Restart the console.",
        "تغير عنوان الحاسوب ({old} -> {ip}): تم تصحيح {path}. أعد تشغيل الجهاز."),
    "network_public_log": (
        "Windows classe ce réseau comme Public : son pare-feu bloque la console.",
        "Windows treats this network as Public: its firewall blocks the console.",
        "يعتبر Windows هذه الشبكة عامة: جداره الناري يحجب الجهاز."),
    "aurora_refreshed": ("Aurora relancé pour mettre à jour sa liste de jeux.",
                         "Aurora restarted to bring its game list up to date.",
                         "تمت إعادة تشغيل Aurora لتحديث قائمة الألعاب."),
    "network_public_ask": (
        "Le passer en Privé maintenant ? Windows va demander l'autorisation administrateur. "
        "Répondez non si vous êtes sur un réseau public (hôtel, café...).",
        "Set it to Private now? Windows will ask for administrator permission. Answer no if you "
        "are on a public network (hotel, café...).",
        "تحويلها إلى خاصة الآن؟ سيطلب Windows إذن المسؤول. أجب بلا إذا كنت على شبكة عامة "
        "(فندق، مقهى...)."),
    "network_private_asked": ("Demande envoyée à Windows : passage du réseau en Privé.",
                              "Request sent to Windows: network set to Private.",
                              "تم إرسال الطلب إلى Windows: تحويل الشبكة إلى خاصة."),
    "network_public_dialog": (
        "Windows classe le réseau de ce PC comme « Public ». Dans ce cas son pare-feu bloque la "
        "console, et les jeux s'arrêtent avec « PC not reachable ».\n\nSi c'est votre réseau "
        "domestique : Paramètres Windows > Réseau et Internet > Ethernet (ou Wi-Fi) > Type de "
        "profil réseau > Privé.\n\nWindows le fait parfois tout seul après un redémarrage de la box.",
        "Windows treats this PC's network as \"Public\". Its firewall then blocks the console, "
        "and games stop with \"PC not reachable\".\n\nIf this is your home network: Windows "
        "Settings > Network & internet > Ethernet (or Wi-Fi) > Network profile type > Private."
        "\n\nWindows sometimes does this on its own after the router restarts.",
        "يعتبر Windows شبكة هذا الحاسوب «عامة». عندها يحجب جداره الناري الجهاز وتتوقف الألعاب "
        "برسالة «PC not reachable».\n\nإذا كانت هذه شبكة منزلك: إعدادات Windows > الشبكة "
        "والإنترنت > Ethernet (أو Wi-Fi) > نوع ملف تعريف الشبكة > خاصة.\n\nقد يفعل Windows ذلك "
        "تلقائيا بعد إعادة تشغيل الموجه."),
    "address_fixed_dialog": (
        "L'adresse de ce PC sur le réseau a changé (souvent après un redémarrage de la box). "
        "NetISO Manager vient de l'écrire sur la console.\n\nRedémarrez la console pour que les "
        "jeux se lancent de nouveau.\n\nPour éviter que cela se reproduise, réservez une adresse "
        "fixe pour ce PC et pour la console dans les réglages de votre box.",
        "This PC's address on the network changed (often after the router restarts). NetISO "
        "Manager has just written it on the console.\n\nRestart the console so games launch "
        "again.\n\nTo stop this from happening again, reserve a fixed address for this PC and "
        "for the console in your router's settings.",
        "تغير عنوان هذا الحاسوب على الشبكة (غالبا بعد إعادة تشغيل الموجه). كتبه NetISO Manager "
        "على الجهاز الآن.\n\nأعد تشغيل الجهاز لكي تعمل الألعاب من جديد.\n\nلتجنب تكرار ذلك، "
        "احجز عنوانا ثابتا لهذا الحاسوب وللجهاز في إعدادات الموجه."),
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
    "iso_truncated": ("ISO incomplet : le fichier est plus court que le disque (téléchargement ou "
                      "copie interrompu). Le jeu planterait sur la console.",
                      "incomplete ISO: the file is shorter than the disc (interrupted download or "
                      "copy). The game would crash on the console.",
                      "ملف ISO ناقص: الملف أقصر من القرص (تنزيل أو نسخ متوقف). ستتعطل اللعبة على "
                      "الجهاز."),
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
