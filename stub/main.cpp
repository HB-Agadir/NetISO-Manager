// NetISO launcher: one copy of this program sits behind every game tile.
// It asks the NetISO.xex plugin to mount the game's ISO from the PC, waits for
// the disc to become readable, then boots it.
//
// game:\netiso.cfg holds the game name on line 1 and, on line 2, the message
// to show when the PC cannot be reached (UTF-8), on line 3 the number of
// discs of the game and on line 4 the size of the plugin's read requests.
// Every step is written to game:\netiso_stub.log.

#include <xtl.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "xkelib.h"

static const DWORD kDiscTimeoutMs = 30000;
// The toast is drawn by the system while this launcher is still running: leaving
// at once to the dashboard dropped it (user report 2026-10-14, "it crashes").
static const DWORD kToastMs = 4000;
static const DWORD kDiscChoiceMs = 2500;
static const char kNoServerEntry[] = "No Server!";
static const WCHAR kDefaultMessage[] = L"NetISO: PC not reachable. Open NetISO Manager.";

static DWORD g_start = 0;

// Opens, appends and closes on every line so the log survives if the title
// is terminated mid-run.
static void Log(const char *fmt, ...)
{
	FILE *log = fopen("game:\\netiso_stub.log", "ab");
	if (log == NULL)
		return;
	fprintf(log, "[%6u ms] ", GetTickCount() - g_start);
	va_list args;
	va_start(args, fmt);
	vfprintf(log, fmt, args);
	va_end(args);
	fputs("\r\n", log);
	fclose(log);
}

static HRESULT Mount(const char *link, const char *device)
{
	char linkPath[64];
	STRING linkName;
	STRING deviceName;
	_snprintf(linkPath, sizeof(linkPath), "\\??\\%s", link);
	linkPath[sizeof(linkPath) - 1] = '\0';
	RtlInitAnsiString(&linkName, linkPath);
	RtlInitAnsiString(&deviceName, device);
	ObDeleteSymbolicLink(&linkName);
	return ObCreateSymbolicLink(&linkName, &deviceName);
}

static void TrimLine(char *line)
{
	size_t len = strlen(line);
	while (len > 0 && (line[len - 1] == '\r' || line[len - 1] == '\n' || line[len - 1] == ' '))
		line[--len] = '\0';
}

static bool ReadConfig(char *name, size_t nameSize, WCHAR *message, int messageChars, int *discs,
	DWORD *requestSize)
{
	char line[512];
	FILE *cfg = fopen("game:\\netiso.cfg", "rb");
	if (cfg == NULL)
		return false;
	bool ok = fgets(name, (int)nameSize, cfg) != NULL;
	*discs = 1;
	*requestSize = 0;
	if (ok && fgets(line, sizeof(line), cfg) != NULL)
	{
		TrimLine(line);
		if (line[0] != '\0')
			MultiByteToWideChar(CP_UTF8, 0, line, -1, message, messageChars);
		if (fgets(line, sizeof(line), cfg) != NULL)
		{
			*discs = atoi(line);
			if (fgets(line, sizeof(line), cfg) != NULL)
				*requestSize = strtoul(line, NULL, 10);
		}
	}
	fclose(cfg);
	if (!ok)
		return false;
	TrimLine(name);
	return name[0] != '\0';
}

// Lets the player pick another disc of a multi-disc game from the console:
// holding the right trigger or right stick button while the tile starts asks
// for the next disc, the left ones for the previous disc. Returns the suffix
// the server understands, or an empty string.
static const char *DiscRequest()
{
	DWORD start = GetTickCount();
	while (GetTickCount() - start < kDiscChoiceMs)
	{
		for (DWORD port = 0; port < 4; port++)
		{
			XINPUT_STATE state;
			if (XInputGetState(port, &state) != ERROR_SUCCESS)
				continue;
			if (state.Gamepad.bRightTrigger > 128 || (state.Gamepad.wButtons & XINPUT_GAMEPAD_RIGHT_THUMB))
				return "#+";
			if (state.Gamepad.bLeftTrigger > 128 || (state.Gamepad.wButtons & XINPUT_GAMEPAD_LEFT_THUMB))
				return "#-";
		}
		Sleep(20);
	}
	return "";
}

// The plugin lists a single "No Server!" entry while it has no connection to the PC.
static bool ServerReachable()
{
	WIN32_FIND_DATA data;
	HANDLE find = FindFirstFile("nisoiso:\\*", &data);
	if (find == INVALID_HANDLE_VALUE)
	{
		Log("plugin list failed, error %u", GetLastError());
		return false;
	}
	FindClose(find);
	Log("plugin first entry: '%s'", data.cFileName);
	return strcmp(data.cFileName, kNoServerEntry) != 0;
}

// Enumerating "<game>\Mount" is what makes the plugin send the mount command.
static void RequestMount(const char *name)
{
	char path[400];
	WIN32_FIND_DATA data;
	_snprintf(path, sizeof(path), "nisoiso:\\%s\\Mount\\*", name);
	path[sizeof(path) - 1] = '\0';
	HANDLE find = FindFirstFile(path, &data);
	if (find != INVALID_HANDLE_VALUE)
		FindClose(find);
}

// NetISO.xex 1.0 calls into xam right after sending a mount. That request
// overlaps with our own launch of the disc and leaves the Guide button dead
// until the next reboot. The call is a single "bl" in the plugin's directory
// handler: it is replaced by a nop for the duration of the mount request and
// put back afterwards, so the plugin is left exactly as it was.
static const DWORD kExitCallAddress = 0x91104DC4;
static const DWORD kExitCallOpcode = 0x48007369; // bl 0x9110C12C
static const DWORD kNopOpcode = 0x60000000;

static bool WritePluginOpcode(DWORD expected, DWORD replacement)
{
	DWORD *call = (DWORD *)kExitCallAddress;
	__try
	{
		DWORD opcode = *call;
		if (opcode == replacement)
			return true;
		if (opcode != expected)
		{
			Log("unexpected opcode 0x%08X at 0x%08X, plugin left untouched", opcode, kExitCallAddress);
			return false;
		}
		*call = replacement;
		__dcbst(0, call);
		__sync();
		__emit(0x4C00012C); // isync
		return *call == replacement;
	}
	__except (EXCEPTION_EXECUTE_HANDLER)
	{
		Log("exception 0x%08X while patching the plugin", GetExceptionCode());
		return false;
	}
}

// The plugin fetches the disc from the PC in requests of at most 0x1000 bytes
// ("cmplwi r4,N / blt / li r4,N"), which caps the speed at about 4 MB/s on a
// link that can carry more than twice that. Raising N to 0x7800 was measured
// at 8.9 MB/s with every byte read back identical. The change stays in the
// plugin's memory until the console restarts.
static const DWORD kCompareAddress = 0x911050E0;
static const DWORD kCompareOpcode = 0x2B040000; // cmplwi cr6,r4,N
static const DWORD kLoadAddress = 0x911050E8;
static const DWORD kLoadOpcode = 0x38800000;    // li r4,N
static const DWORD kMaxRequestSize = 0x7800;    // largest sector multiple "li" can load

static bool WriteOpcode(DWORD address, DWORD value)
{
	DWORD *code = (DWORD *)address;
	*code = value;
	__dcbst(0, code);
	__sync();
	__emit(0x4C00012C); // isync
	return *code == value;
}

static bool SetRequestSize(DWORD size)
{
	if (size < 0x1000 || size > kMaxRequestSize || (size & 0x7FF) != 0)
		return false;
	__try
	{
		DWORD compare = *(DWORD *)kCompareAddress;
		DWORD load = *(DWORD *)kLoadAddress;
		DWORD current = load & 0xFFFF;
		if ((compare & 0xFFFF0000) != kCompareOpcode || (load & 0xFFFF0000) != kLoadOpcode
			|| (compare & 0xFFFF) != current)
		{
			Log("unexpected read code %08X %08X, request size left untouched", compare, load);
			return false;
		}
		if (current == size)
			return true;
		// The comparison and the value must never let a request exceed what
		// is left to read: grow the comparison first, shrink the value first.
		if (size > current)
			return WriteOpcode(kCompareAddress, kCompareOpcode | size)
				&& WriteOpcode(kLoadAddress, kLoadOpcode | size);
		return WriteOpcode(kLoadAddress, kLoadOpcode | size)
			&& WriteOpcode(kCompareAddress, kCompareOpcode | size);
	}
	__except (EXCEPTION_EXECUTE_HANDLER)
	{
		Log("exception 0x%08X while setting the request size", GetExceptionCode());
		return false;
	}
}

static bool WaitForDisc(DWORD timeoutMs)
{
	DWORD start = GetTickCount();
	while (GetTickCount() - start < timeoutMs)
	{
		if (GetFileAttributes("nisodvd:\\default.xex") != INVALID_FILE_ATTRIBUTES)
			return true;
		Sleep(100);
	}
	return false;
}

// Queues a toast for the dashboard to show, then hands control back to it.
static void FailToDashboard(const WCHAR *message)
{
	XNotifyQueueUI(XNOTIFYUI_TYPE_GENERIC, 0, 2, (PWCHAR)message, NULL);
	Sleep(kToastMs);
	Log("returning to dashboard");
	XLaunchNewImage(XLAUNCH_KEYWORD_DEFAULT_APP, 0);
}

void __cdecl main()
{
	char name[256];
	WCHAR message[256];

	g_start = GetTickCount();
	DeleteFile("game:\\netiso_stub.log");
	Log("netiso launcher 1.1");
	wcscpy(message, kDefaultMessage);

	int discs = 1;
	DWORD requestSize = 0;
	if (!ReadConfig(name, sizeof(name), message, 256, &discs, &requestSize))
	{
		Log("netiso.cfg missing or empty");
		FailToDashboard(message);
		return;
	}
	Log("game: '%s'", name);

	HRESULT plugin = Mount("nisoiso:", "\\Device\\NetIso");
	Mount("nisodvd:", "\\Device\\Cdrom0");
	if (FAILED(plugin))
	{
		Log("NetISO plugin not loaded, link error 0x%08X", plugin);
		FailToDashboard(message);
		return;
	}
	if (!ServerReachable())
	{
		Log("PC server not reachable");
		FailToDashboard(message);
		return;
	}

	if (discs > 1)
	{
		const char *request = DiscRequest();
		Log("%d discs, request '%s'", discs, request);
		strncat(name, request, sizeof(name) - strlen(name) - 1);
	}

	bool patched = WritePluginOpcode(kExitCallOpcode, kNopOpcode);
	Log("mount request, plugin exit call disabled: %d", patched);
	RequestMount(name);
	if (patched)
		WritePluginOpcode(kNopOpcode, kExitCallOpcode);

	if (!WaitForDisc(kDiscTimeoutMs))
	{
		Log("disc not ready after %u ms", kDiscTimeoutMs);
		FailToDashboard(message);
		return;
	}
	if (requestSize != 0)
		Log("read request size 0x%X: %d", requestSize, SetRequestSize(requestSize));
	Log("disc ready, launching");
	XLaunchNewImage("nisodvd:\\default.xex", 0);
}
