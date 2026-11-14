"""Ícone na bandeja do Windows (área de notificação), só ctypes da biblioteca padrão.

Roda numa thread com janela oculta própria; o Tk não é thread-safe, então os cliques viram itens numa
`queue.Queue` que o PetApp esvazia no tick. Clique esquerdo = item 0; botão direito abre um menu com `itens()`.
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


def ico(png: bytes, lado: int) -> bytes:
    """Arquivo .ico com um PNG dentro (Windows Vista+ lê direto)."""
    return struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", lado % 256, lado % 256, 0, 0, 1, 32,
                                                      len(png), 22) + png


class Bandeja:
    def __init__(self, icone: str, dica: str, itens):
        self.fila: queue.Queue = queue.Queue()
        self.icone, self.dica, self.itens = icone, dica, itens
        self.hwnd = None
        self.thread = threading.Thread(target=self._rodar, daemon=True, name="bandeja")
        self.thread.start()

    def fechar(self):
        """Tira o ícone (sem isso fica um ícone fantasma até passar o mouse)."""
        if self.hwnd:
            ctypes.windll.user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
            self.thread.join(1)

    def _rodar(self):
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
        recriada = u.RegisterWindowMessageW("TaskbarCreated")   # o Explorer reiniciou: pôr o ícone de novo

        nid = NOTIFYICONDATAW(cbSize=ctypes.sizeof(NOTIFYICONDATAW), uID=1,
                              uFlags=NIF_MESSAGE | NIF_ICON | NIF_TIP, uCallbackMessage=CALLBACK)
        nid.szTip = self.dica[:127]
        nid.hIcon = u.LoadImageW(None, self.icone, 1, 0, 0, 0x10 | 0x40)    # IMAGE_ICON, FROMFILE|DEFAULTSIZE

        def menu():
            m = u.CreatePopupMenu()
            for i, txt in enumerate(self.itens()):
                u.AppendMenuW(m, 0, i + 1, txt)
            pt = W.POINT()
            u.GetCursorPos(ctypes.byref(pt))
            u.SetForegroundWindow(self.hwnd)                   # sem isso o menu não fecha ao clicar fora
            esc = u.TrackPopupMenu(m, 0x0100 | 0x0080, pt.x, pt.y, 0, self.hwnd, None)  # RETURNCMD|NONOTIFY
            u.PostMessageW(self.hwnd, WM_NULL, 0, 0)
            u.DestroyMenu(m)
            if esc:
                self.fila.put(esc - 1)

        def proc(hwnd, msg, wp, lp):
            if msg == CALLBACK:
                if lp & 0xFFFF == WM_LBUTTONUP:
                    self.fila.put(0)
                elif lp & 0xFFFF == WM_RBUTTONUP:
                    menu()
                return 0
            if msg == recriada:
                sh.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
            elif msg == WM_DESTROY:
                sh.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
                u.PostQuitMessage(0)
                return 0
            return u.DefWindowProcW(hwnd, msg, wp, lp)

        self._proc = WNDPROC(proc)                              # referência viva, senão o GC solta o callback
        inst = k.GetModuleHandleW(None)
        u.RegisterClassW(ctypes.byref(WNDCLASSW(lpfnWndProc=self._proc, hInstance=inst,
                                                lpszClassName="AgentTokenlikeBandeja")))
        self.hwnd = u.CreateWindowExW(0, "AgentTokenlikeBandeja", self.dica, 0, 0, 0, 0, 0, None, None, inst, None)
        nid.hWnd = self.hwnd
        sh.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        msg = W.MSG()
        while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            u.TranslateMessage(ctypes.byref(msg))
            u.DispatchMessageW(ctypes.byref(msg))
