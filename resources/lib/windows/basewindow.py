"""
Base window class for most other windows
"""
import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.utils import SharedProperties
from resources.lib.videohelpers import VideoHelpers

class BaseWindow(xbmcgui.WindowXML):
    """
    Base window class for most other windows
    """
    OPTIONICON=9001
    OPTIONLABEL=9002
    def __init__(self, xmlFilename, scriptPath, defaultSkin = "Default", defaultRes = "720p",
                 isMedia = False, addon: xbmcaddon.Addon=None):
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes, isMedia)
        self.addon = addon
        self.sharedproperties = SharedProperties(addon)
        self.sortby = None
        self.sortorder = None
        self.recordingfilter = None
        self.videoHelper = VideoHelpers(self.addon)

    def onAction(self, action):
        super().onAction(action)
        if action.getId() == xbmcgui.ACTION_STOP:
            xbmc.log('Window onAction STOP', xbmc.LOGDEBUG)
            return

        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU or action.getId() == xbmcgui.ACTION_NAV_BACK:
            xbmc.log('Window onAction PREVIOUS or BACK', xbmc.LOGDEBUG)
            return

        if action.getId() == xbmcgui.ACTION_CONTEXT_MENU:
            self.show_context_menu()

    def onClick(self, controlId):
        if controlId in [self.OPTIONICON,self.OPTIONLABEL]:
            xbmc.log('Window OPTION Icon', xbmc.LOGDEBUG)
            self.show_options()
            return
        super().onClick(controlId)

    def onFocus(self, controlId):
        # pylint: disable=useless-parent-delegation
        return super().onFocus(controlId)

    def show_options(self):
        """
        Function to be called from a child window to show the sidewindow
        
        :param self: 
        """
        # pylint: disable=import-outside-toplevel
        from resources.lib.windows.sidewindow import load_sidewindow
        window = load_sidewindow(self.addon, self)
        self.sortby, self.sortorder = self.sharedproperties.get_sort_options_channels()
        self.recordingfilter = self.sharedproperties.get_recording_filter()
        del window
        self.options_selected()

    def show_context_menu(self):
        """
        Should be overriden to receive signal that context menu should popup
        """

    def options_selected(self):
        """
        Should be overriden to receive signal that options were selected
        in the side window
        """
    def __del__(self):
        self.videoHelper.requestorCallbackStop = None
        self.videoHelper.player_stopped()
        xbmc.log(f'BaseWindow destroyed {self.__class__.__name__}',xbmc.LOGDEBUG)
