// Phase 0 probe: asks the NetISO plugin to mount one ISO, then boots the disc.
// The ISO name is the first line of game:\netiso.cfg. Every step is written
// to game:\netiso_stub.log so the result can be read back over FTP.

#include <xtl.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "xkelib.h"

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

// Line 1 is the ISO name. Optional line 2 is the delay in milliseconds
// between the mount request and the launch of the disc.
static bool ReadConfig(char *name, size_t size, DWORD *delayMs)
{
	char line[32];
	FILE *cfg = fopen("game:\\netiso.cfg", "rb");
	if (cfg == NULL)
		return false;
	bool ok = fgets(name, (int)size, cfg) != NULL;
	*delayMs = 0;
	if (ok && fgets(line, sizeof(line), cfg) != NULL)
		*delayMs = strtoul(line, NULL, 10);
	fclose(cfg);
	if (!ok)
		return false;
	size_t len = strlen(name);
	while (len > 0 && (name[len - 1] == '\r' || name[len - 1] == '\n' || name[len - 1] == ' '))
		name[--len] = '\0';
	return len > 0;
}

// Lists a directory of the NetISO device. Enumerating "<iso>\Mount" is what
// makes the plugin send the mount command to the server.
static int ListDir(const char *pattern)
{
	WIN32_FIND_DATA data;
	int count = 0;
	HANDLE find = FindFirstFile(pattern, &data);
	if (find == INVALID_HANDLE_VALUE)
	{
		Log("  list '%s' -> no entry, error %u", pattern, GetLastError());
		return 0;
	}
	do
	{
		Log("  list '%s' -> '%s'", pattern, data.cFileName);
		count++;
	} while (count < 500 && FindNextFile(find, &data));
	FindClose(find);
	return count;
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

// Polls for the mounted disc and logs a heartbeat and every state change.
static bool WaitForDisc(DWORD timeoutMs)
{
	DWORD start = GetTickCount();
	DWORD lastAlive = 0;
	DWORD lastError = 0xFFFFFFFF;
	while (GetTickCount() - start < timeoutMs)
	{
		DWORD elapsed = GetTickCount() - start;
		if (elapsed - lastAlive >= 500)
		{
			lastAlive = elapsed;
			Log("alive");
		}
		if (GetFileAttributes("nisodvd:\\default.xex") != INVALID_FILE_ATTRIBUTES)
			return true;
		DWORD error = GetLastError();
		if (error != lastError)
		{
			lastError = error;
			Log("nisodvd:\\default.xex not visible, error %u", error);
		}
		Sleep(100);
	}
	return false;
}

void __cdecl main()
{
	char iso[256];
	char path[400];
	DWORD delayMs = 0;

	g_start = GetTickCount();
	DeleteFile("game:\\netiso_stub.log");
	Log("netiso stub phase 0, build 7");
	Log("link nisoiso: -> 0x%08X", Mount("nisoiso:", "\\Device\\NetIso"));
	Log("link nisodvd: -> 0x%08X", Mount("nisodvd:", "\\Device\\Cdrom0"));

	if (!ReadConfig(iso, sizeof(iso), &delayMs))
	{
		Log("netiso.cfg missing or empty, listing server only");
		ListDir("nisoiso:\\*");
	}
	else
	{
		Log("iso: '%s'", iso);

		_snprintf(path, sizeof(path), "nisoiso:\\%s\\Mount\\*", iso);
		path[sizeof(path) - 1] = '\0';
		bool patched = WritePluginOpcode(kExitCallOpcode, kNopOpcode);
		Log("plugin exit call disabled: %d", patched);
		Log("sending mount request");
		ListDir(path);
		Log("mount request returned");
		if (patched)
			Log("plugin exit call restored: %d", WritePluginOpcode(kNopOpcode, kExitCallOpcode));

		if (WaitForDisc(30000))
		{
			Log("disc ready, launching nisodvd:\\default.xex");
			XLaunchNewImage("nisodvd:\\default.xex", 0);
			Log("XLaunchNewImage returned, error %u", GetLastError());
		}
		else
		{
			Log("disc not ready after 30 s");
		}
	}

	Log("returning to dashboard");
	XLaunchNewImage(XLAUNCH_KEYWORD_DEFAULT_APP, 0);
}
