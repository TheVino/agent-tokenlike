"""Windows tray icon (notification area), using only ctypes from the standard library.

Runs in a thread with its own hidden window; Tk is not thread-safe, so clicks become items in a
`queue.Queue` that PetApp drains. Left click = item 0; right click opens a menu with `items()`.
"""
from __future__ import annotations

import ctypes
import queue
import struct
import threading
from ctypes import wintypes as W

WM_DESTROY, WM_CLOSE, WM_NULL, WM_APP = 0x0002, 0x0010, 0x0000, 0x8000
WM_LBUTTONUP, WM_RBUTTONUP = 0x0202, 0x0205
NIM_ADD, NIM_DELETE = 0, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 1, 2, 4
CALLBACK = WM_APP + 1

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, W.HWND, W.UINT, W.WPARAM, W.LPARAM)


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", W.DWORD), ("hWnd", W.HWND), ("uID", W.UINT), ("uFlags", W.UINT),
                ("uCallbackMessage", W.UINT), ("hIcon", W.HICON), ("szTip", W.WCHAR * 128),
                ("dwState", W.DWORD), ("dwStateMask", W.DWORD), ("szInfo", W.WCHAR * 256),
                ("uVersion", W.UINT), ("szInfoTitle", W.WCHAR * 64), ("dwInfoFlags", W.DWORD),
                ("guidItem", ctypes.c_byte * 16), ("hBalloonIcon", W.HICON)]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", W.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", W.HINSTANCE), ("hIcon", W.HICON),
                ("hCursor", W.HANDLE), ("hbrBackground", W.HANDLE), ("lpszMenuName", W.LPCWSTR),
                ("lpszClassName", W.LPCWSTR)]


def ico(png: bytes, side: int) -> bytes:
    """.ico file with a PNG inside (Windows Vista+ reads it directly)."""
    return struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", side % 256, side % 256, 0, 0, 1, 32,
                                                      len(png), 22) + png


class Bandeja:
    def __init__(self, icon_file: str, tooltip: str, items):
        self.events: queue.Queue = queue.Queue()
        self.icon_file, self.tooltip, self.items = icon_file, tooltip, items
        self.hwnd = None
        self.thread = threading.Thread(target=self._loop, daemon=True, name="tray")
        self.thread.start()

    def shutdown(self):
        """Removes the icon (without this a ghost icon stays until the mouse passes over it)."""
        if self.hwnd:
            ctypes.windll.user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
            self.thread.join(1)

    def _loop(self):
        u, sh, k = ctypes.windll.user32, ctypes.windll.shell32, ctypes.windll.kernel32
        u.DefWindowProcW.argtypes = (W.HWND, W.UINT, W.WPARAM, W.LPARAM)
        u.DefWindowProcW.restype = LRESULT
        u.CreateWindowExW.restype = W.HWND
        u.CreateWindowExW.argtypes = (W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD, ctypes.c_int, ctypes.c_int,
                                      ctypes.c_int, ctypes.c_int, W.HWND, W.HMENU, W.HINSTANCE, W.LPVOID)
        u.LoadImageW.restype = W.HANDLE
        u.LoadImageW.argtypes = (W.HINSTANCE, W.LPCWSTR, W.UINT, ctypes.c_int, ctypes.c_int, W.UINT)
        u.CreatePopupMenu.restype = W.HMENU
        u.AppendMenuW.argtypes = (W.HMENU, W.UINT, ctypes.c_size_t, W.LPCWSTR)
        u.TrackPopupMenu.argtypes = (W.HMENU, W.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, W.HWND, W.LPVOID)
        u.DestroyMenu.argtypes = (W.HMENU,)
        u.PostMessageW.argtypes = (W.HWND, W.UINT, W.WPARAM, W.LPARAM)
        sh.Shell_NotifyIconW.argtypes = (W.DWORD, ctypes.POINTER(NOTIFYICONDATAW))
        k.GetModuleHandleW.restype = W.HMODULE
        recreated = u.RegisterWindowMessageW("TaskbarCreated")   # Explorer restarted: add the icon again

        nid = NOTIFYICONDATAW(cbSize=ctypes.sizeof(NOTIFYICONDATAW), uID=1,
                              uFlags=NIF_MESSAGE | NIF_ICON | NIF_TIP, uCallbackMessage=CALLBACK)
        nid.szTip = self.tooltip[:127]
        nid.hIcon = u.LoadImageW(None, self.icon_file, 1, 0, 0, 0x10 | 0x40)    # IMAGE_ICON, FROMFILE|DEFAULTSIZE

        def menu():
            m = u.CreatePopupMenu()
            for i, txt in enumerate(self.items()):
                u.AppendMenuW(m, 0, i + 1, txt)
            pt = W.POINT()
            u.GetCursorPos(ctypes.byref(pt))
            u.SetForegroundWindow(self.hwnd)                   # without this the menu does not close when clicking outside
            esc = u.TrackPopupMenu(m, 0x0100 | 0x0080, pt.x, pt.y, 0, self.hwnd, None)  # RETURNCMD|NONOTIFY
            u.PostMessageW(self.hwnd, WM_NULL, 0, 0)
            u.DestroyMenu(m)
            if esc:
                self.events.put(esc - 1)

        def proc(hwnd, msg, wp, lp):
            if msg == CALLBACK:
                if lp & 0xFFFF == WM_LBUTTONUP:
                    self.events.put(0)
                elif lp & 0xFFFF == WM_RBUTTONUP:
                    menu()
                return 0
            if msg == recreated:
                sh.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
            elif msg == WM_DESTROY:
                sh.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
                u.PostQuitMessage(0)
                return 0
            return u.DefWindowProcW(hwnd, msg, wp, lp)

        self._proc = WNDPROC(proc)                              # keep a live reference, otherwise the GC frees the callback
        inst = k.GetModuleHandleW(None)
        u.RegisterClassW(ctypes.byref(WNDCLASSW(lpfnWndProc=self._proc, hInstance=inst,
                                                lpszClassName="AgentTokenlikeBandeja")))
        self.hwnd = u.CreateWindowExW(0, "AgentTokenlikeBandeja", self.tooltip, 0, 0, 0, 0, 0, None, None, inst, None)
        nid.hWnd = self.hwnd
        sh.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        msg = W.MSG()
        while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            u.TranslateMessage(ctypes.byref(msg))
            u.DispatchMessageW(ctypes.byref(msg))
