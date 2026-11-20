"""ui/mac_window.py — the Mac's tall title bar, asked of AppKit directly.

Qt draws its content under a transparent title bar (``ExpandedClientAreaHint``
and ``NoTitleBarBackgroundHint``) but has no way to ask for the taller title
bar a Mac app with a toolbar has, where the traffic lights sit at the bar's
centre. AppKit gives one to a window that carries a toolbar, so an empty
``NSToolbar`` in the unified style is attached and the system title is hidden;
the window's own top bar is then drawn in that band.

This talks to the Objective-C runtime through ctypes, so it needs nothing
installed. Anything that fails leaves the window as Qt made it.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import sys

# The height AppKit gives a compact unified title bar with a toolbar, in points.
TALL_TITLE_BAR = 40
# NSWindowToolbarStyleUnifiedCompact, NSWindowTitleHidden and
# NSWindowStyleMaskFullSizeContentView. The compact style keeps the band a
# toolbar gives, with the traffic lights at its centre, and the smaller corner
# radius macOS gives a window whose toolbar is compact.
_TOOLBAR_STYLE_UNIFIED = 4
_TITLE_HIDDEN = 1
_FULL_SIZE_CONTENT = 1 << 15

_objc = None


def _runtime():
    global _objc
    if _objc is None:
        _objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
        ctypes.cdll.LoadLibrary(ctypes.util.find_library("AppKit"))
        _objc.objc_getClass.restype = ctypes.c_void_p
        _objc.objc_getClass.argtypes = [ctypes.c_char_p]
        _objc.sel_registerName.restype = ctypes.c_void_p
        _objc.sel_registerName.argtypes = [ctypes.c_char_p]
    return _objc


def _send(receiver, selector: str, *args, restype=ctypes.c_void_p, argtypes=()):
    """One Objective-C message, with its signature spelled out: on Apple
    silicon a message's arguments are passed as the signature says, never as
    varargs."""
    objc = _runtime()
    address = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
    function = ctypes.CFUNCTYPE(restype, ctypes.c_void_p, ctypes.c_void_p, *argtypes)(address)
    return function(receiver, objc.sel_registerName(selector.encode()), *args)


def _class(name: str):
    return _runtime().objc_getClass(name.encode())


def tall_title_bar(widget) -> bool:
    """Give ``widget``'s window the tall unified title bar, its title hidden and
    its content running under the bar. Returns whether it now has one."""
    if sys.platform != "darwin":
        return False
    try:
        view = ctypes.c_void_p(int(widget.winId()))
        window = _send(view, "window")
        if not window:
            return False
        name = _send(
            _class("NSString"),
            "stringWithUTF8String:",
            b"BristolTickets",
            argtypes=(ctypes.c_char_p,),
        )
        toolbar = _send(
            _send(_class("NSToolbar"), "alloc"),
            "initWithIdentifier:",
            name,
            argtypes=(ctypes.c_void_p,),
        )
        _send(toolbar, "setShowsBaselineSeparator:", False, restype=None, argtypes=(ctypes.c_bool,))
        _send(window, "setToolbar:", toolbar, restype=None, argtypes=(ctypes.c_void_p,))
        _send(
            window,
            "setToolbarStyle:",
            _TOOLBAR_STYLE_UNIFIED,
            restype=None,
            argtypes=(ctypes.c_long,),
        )
        _send(window, "setTitleVisibility:", _TITLE_HIDDEN, restype=None, argtypes=(ctypes.c_long,))
        _send(
            window, "setTitlebarAppearsTransparent:", True, restype=None, argtypes=(ctypes.c_bool,)
        )
        mask = _send(window, "styleMask", restype=ctypes.c_ulong)
        _send(
            window,
            "setStyleMask:",
            mask | _FULL_SIZE_CONTENT,
            restype=None,
            argtypes=(ctypes.c_ulong,),
        )
        return True
    except Exception:
        return False


def clear_backing(widget) -> bool:
    """Make ``widget``'s window see-through where nothing is painted, so a
    translucent paint shows the windows behind it. Returns whether it is."""
    if sys.platform != "darwin":
        return False
    try:
        view = ctypes.c_void_p(int(widget.winId()))
        window = _send(view, "window")
        if not window:
            return False
        _send(window, "setOpaque:", False, restype=None, argtypes=(ctypes.c_bool,))
        _send(
            window,
            "setBackgroundColor:",
            _send(_class("NSColor"), "clearColor"),
            restype=None,
            argtypes=(ctypes.c_void_p,),
        )
        _send(window, "setHasShadow:", False, restype=None, argtypes=(ctypes.c_bool,))
        return True
    except Exception:
        return False
