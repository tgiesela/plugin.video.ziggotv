"""
The actual addon implementation. From here the ziggo plugin menus are constructed.
"""

import traceback

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.formcreator import FormCreator
from resources.lib.utils import WebException
from resources.lib.windows.homewindow import load_homewindow

def process_xml_forms():
    """
    Function to process includes in an XML element.
    
    """
    forms = [
        'channels.xml.templ',
        'movies.xml.templ',
        'screen-epg.xml.templ',
        'recordings.xml.templ',
        'ziggohome.xml.templ',
        'sidewindow.xml.templ'
    ]
    fc = FormCreator()
    for form in forms:
        fc.processxml(form)
        xbmc.log(f'Processed form {form}', xbmc.LOGDEBUG)
    fc.savestate(fc.statefile)
    fc = None

if __name__ == '__main__':
    from resources.lib.utils import invoke_debugger
    invoke_debugger(False, 'vscode')

    try:
        ADDON: xbmcaddon.Addon = xbmcaddon.Addon()
        process_xml_forms()
        load_homewindow(ADDON)

    except WebException as exc:
        xbmcgui.Dialog().ok('Error', '{0}'.format(exc.response))
        xbmc.log(traceback.format_exc(), xbmc.LOGDEBUG)
    # pylint: disable=broad-exception-caught
    except Exception as exc:
        xbmcgui.Dialog().ok('Error', f'{exc}')
        xbmc.log(traceback.format_exc(), xbmc.LOGDEBUG)
