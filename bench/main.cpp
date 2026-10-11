// NetISO read benchmark (development tool, not shipped).
// Mounts the game named on line 1 of game:\bench.cfg, then reads slices of the
// file named on line 2 with different plugin request sizes and writes speed
// and a checksum of each slice to game:\bench.log.

#include <xtl.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "xkelib.h"

static const DWORD kSliceBytes = 64 * 1024 * 1024;
static const DWORD kBufferBytes = 1024 * 1024;

static void Log(const char *fmt, ...)
{
	FILE *log = fopen("game:\\bench.log", "ab");
	if (log == NULL)
		return;
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

// Replaces one instruction of the loaded plugin after checking what is there.
static bool Patch(DWORD address, DWORD expected, DWORD replacement)
{
	DWORD *code = (DWORD *)address;
	__try
	{
		if (*code != expected)
		{
			Log("unexpected opcode 0x%08X at 0x%08X (wanted 0x%08X)", *code, address, expected);
			return false;
		}
		*code = replacement;
		__dcbst(0, code);
		__sync();
		__emit(0x4C00012C); // isync
		return *code == replacement;
	}
	__except (EXCEPTION_EXECUTE_HANDLER)
	{
		Log("exception 0x%08X while patching 0x%08X", GetExceptionCode(), address);
		return false;
	}
}

// The plugin splits every disc read into network requests of at most 0x1000
// bytes: "cmplwi r4,0x1000 / blt / li r4,0x1000". Both immediates are changed,
// the comparison first so that the request size can never exceed what is left.
static const DWORD kCompareAddress = 0x911050E0;
static const DWORD kLoadAddress = 0x911050E8;
static DWORD g_requestSize = 0x1000;

static bool SetRequestSize(DWORD size)
{
	if (size == g_requestSize)
		return true;
	bool ok;
	if (size > g_requestSize)
		ok = Patch(kCompareAddress, 0x2B040000 | g_requestSize, 0x2B040000 | size)
			&& Patch(kLoadAddress, 0x38800000 | g_requestSize, 0x38800000 | size);
	else
		ok = Patch(kLoadAddress, 0x38800000 | g_requestSize, 0x38800000 | size)
			&& Patch(kCompareAddress, 0x2B040000 | g_requestSize, 0x2B040000 | size);
	if (ok)
		g_requestSize = size;
	return ok;
}

static void ReadSlice(const char *path, DWORD sliceIndex, DWORD requestSize, BYTE *buffer)
{
	if (!SetRequestSize(requestSize))
	{
		Log("slice %u: could not set request size 0x%X", sliceIndex, requestSize);
		return;
	}
	HANDLE file = CreateFile(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
		FILE_FLAG_NO_BUFFERING | FILE_FLAG_SEQUENTIAL_SCAN, NULL);
	if (file == INVALID_HANDLE_VALUE)
	{
		Log("slice %u: cannot open '%s', error %u", sliceIndex, path, GetLastError());
		return;
	}
	LARGE_INTEGER position;
	position.QuadPart = (LONGLONG)sliceIndex * kSliceBytes;
	SetFilePointerEx(file, position, NULL, FILE_BEGIN);

	LARGE_INTEGER frequency, before, after;
	QueryPerformanceFrequency(&frequency);
	LONGLONG ticks = 0;
	DWORD total = 0;
	DWORD hash = 2166136261u; // FNV-1a
	while (total < kSliceBytes)
	{
		DWORD got = 0;
		QueryPerformanceCounter(&before);
		BOOL ok = ReadFile(file, buffer, kBufferBytes, &got, NULL);
		QueryPerformanceCounter(&after);
		ticks += after.QuadPart - before.QuadPart;
		if (!ok || got == 0)
		{
			Log("slice %u: read stopped at %u bytes, error %u", sliceIndex, total, GetLastError());
			break;
		}
		for (DWORD i = 0; i < got; i++)
			hash = (hash ^ buffer[i]) * 16777619u;
		total += got;
	}
	CloseHandle(file);
	double seconds = (double)ticks / (double)frequency.QuadPart;
	Log("slice %u  request 0x%04X  %u bytes in %.2f s  %.2f MB/s  fnv %08X",
		sliceIndex, requestSize, total, seconds, seconds > 0 ? total / seconds / 1048576.0 : 0.0, hash);
}

void __cdecl main()
{
	char name[256] = "";
	char file[256] = "";
	char path[600];
	WIN32_FIND_DATA data;

	DeleteFile("game:\\bench.log");
	Log("netiso bench");
	FILE *cfg = fopen("game:\\bench.cfg", "rb");
	if (cfg != NULL)
	{
		fgets(name, sizeof(name), cfg);
		fgets(file, sizeof(file), cfg);
		fclose(cfg);
	}
	TrimLine(name);
	TrimLine(file);
	Log("game '%s' file '%s'", name, file);

	Mount("nisoiso:", "\\Device\\NetIso");
	Mount("nisodvd:", "\\Device\\Cdrom0");

	// Same precaution as the launcher: keep the plugin from sending the console
	// back to the dashboard while the mount is requested.
	bool exitDisabled = Patch(0x91104DC4, 0x48007369, 0x60000000);
	_snprintf(path, sizeof(path), "nisoiso:\\%s\\Mount\\*", name);
	HANDLE find = FindFirstFile(path, &data);
	if (find != INVALID_HANDLE_VALUE)
		FindClose(find);
	if (exitDisabled)
		Patch(0x91104DC4, 0x60000000, 0x48007369);

	_snprintf(path, sizeof(path), "nisodvd:\\%s", file);
	DWORD start = GetTickCount();
	while (GetFileAttributes(path) == INVALID_FILE_ATTRIBUTES && GetTickCount() - start < 20000)
		Sleep(100);
	if (GetFileAttributes(path) == INVALID_FILE_ATTRIBUTES)
	{
		Log("file not visible after 20 s, error %u", GetLastError());
	}
	else
	{
		BYTE *buffer = (BYTE *)VirtualAlloc(NULL, kBufferBytes, MEM_COMMIT, PAGE_READWRITE);
		if (buffer == NULL)
		{
			Log("no memory for the read buffer");
		}
		else
		{
			ReadSlice(path, 0, 0x1000, buffer);
			ReadSlice(path, 1, 0x4000, buffer);
			ReadSlice(path, 2, 0x7800, buffer);
			ReadSlice(path, 3, 0x1000, buffer);
			SetRequestSize(0x1000);
			VirtualFree(buffer, 0, MEM_RELEASE);
		}
	}
	Log("request size back to 0x%X", g_requestSize);
	Log("done");
	XLaunchNewImage(XLAUNCH_KEYWORD_DEFAULT_APP, 0);
}
