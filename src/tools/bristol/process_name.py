"""process_name.py — the name macOS shows for the running app.

A source run is a Python process, and macOS titles the application menu, the
Dock tile and the Force Quit list after the bundle the process belongs to,
which is Python's. Writing ``CFBundleName`` into that bundle's info dictionary
before Qt starts AppKit makes the menu read as the app's own name.

This talks to the Objective-C runtime through ctypes, so it needs nothing
installed. Off macOS, and wherever the runtime does not answer as expected, it
does nothing: the name is cosmetic and never worth a failed launch.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import sys

_FOUNDATION = "/System/Library/Frameworks/Foundation.framework/Foundation"


def set_process_name(name: str) -> bool:
    """Title the running process ``name`` in the menu bar. Call before the
    QApplication is created. Returns whether the name was written."""
    if sys.platform != "darwin":
        return False
    try:
        objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
        ctypes.cdll.LoadLibrary(_FOUNDATION)
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        address = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value

        # objc_msgSend takes whatever the method takes, so each shape it is
        # called with gets a prototype of its own.
        send0 = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(address)
        send_str = ctypes.CFUNCTYPE(
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p
        )(address)
        send2 = ctypes.CFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
        )(address)

        def cls(n):
            return objc.objc_getClass(n.encode())

        def sel(n):
            return objc.sel_registerName(n.encode())

        def nsstring(text: str):
            return send_str(cls("NSString"), sel("stringWithUTF8String:"), text.encode("utf-8"))

        bundle = send0(cls("NSBundle"), sel("mainBundle"))
        info = send0(bundle, sel("infoDictionary")) if bundle else None
        if not info:
            return False
        send2(info, sel("setObject:forKey:"), nsstring(name), nsstring("CFBundleName"))
        return True
    except (OSError, AttributeError, TypeError, ValueError):
        return False
