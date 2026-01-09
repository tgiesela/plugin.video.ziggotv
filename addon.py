"""
The actual addon implementation. From here the ziggo plugin menus are constructed.
"""

import traceback

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.utils import WebException
from resources.lib.windows.homewindow import loadhomeWindow

if __name__ == '__main__':
    from resources.lib.utils import invoke_debugger
    invoke_debugger(False, 'vscode')

    try:
        ADDON: xbmcaddon.Addon = xbmcaddon.Addon()
        loadhomeWindow(ADDON)

    except WebException as exc:
        xbmcgui.Dialog().ok('Error', '{0}'.format(exc.response))
        xbmc.log(traceback.format_exc(), xbmc.LOGDEBUG)
    # pylint: disable=broad-exception-caught
    except Exception as exc:
        xbmcgui.Dialog().ok('Error', f'{exc}')
        xbmc.log(traceback.format_exc(), xbmc.LOGDEBUG)
