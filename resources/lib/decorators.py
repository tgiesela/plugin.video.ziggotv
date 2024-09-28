"""
Module containing decorators used when debugging/testing
"""
import functools
from urllib.parse import urlparse

import xbmc


def debug(func):
    """Print the function signature and return value, especially in Kodi"""

    @functools.wraps(func)
    def wrapper_debug(*args, **kwargs):
        argsRepr = [repr(a) for a in args]
        kwargsRepr = [f"{k}={repr(v)}" for k, v in kwargs.items()]
        # pylint: disable=import-outside-toplevel
        from resources.lib.proxyserver import HTTPRequestHandler
        for a in args:
            if isinstance(a, HTTPRequestHandler):
                xbmc.log(f'HTTPRequestHandler.path={urlparse(a.path)}', xbmc.LOGDEBUG)
        signature = ", ".join(argsRepr + kwargsRepr)
        xbmc.log(f"Calling {func.__name__}({signature})", xbmc.LOGDEBUG)
        value = func(*args, **kwargs)
        xbmc.log(f"{func.__name__}() returned {repr(value)}", xbmc.LOGDEBUG)
        return value

    return wrapper_debug
