import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.utils import SharedProperties

class baseWindow(xbmcgui.WindowXML):
    OPTIONICON=9001
    OPTIONLABEL=9002
    def __init__(self, xmlFilename, scriptPath, defaultSkin = "Default", defaultRes = "720p", isMedia = False, addon: xbmcaddon.Addon=None):
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes, isMedia)
        self.addon = addon
        self.sharedproperties = SharedProperties(addon)

    def get_subclass_name(self):
        return self.__class__.__name__

    def onAction(self, action):
        super().onAction(action)
        if action.getId() == xbmcgui.ACTION_STOP:
            xbmc.log(f'Window onAction STOP', xbmc.LOGDEBUG)
            return

        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU or action.getId() == xbmcgui.ACTION_NAV_BACK:
            xbmc.log(f'Window onAction PREVIOUS or BACK', xbmc.LOGDEBUG)
            return
        
        if action.getId() == xbmcgui.ACTION_CONTEXT_MENU:
            self.showContextMenu()

    def onClick(self, controlId):
        if controlId in [self.OPTIONICON,self.OPTIONLABEL]:
            xbmc.log(f'Window OPTION Icon', xbmc.LOGDEBUG)
            self.showOptions()
            return
        super().onClick(controlId)

    def onFocus(self, controlId):
        return super().onFocus(controlId)

    def showOptions(self):
        from resources.lib.windows.sidewindow import loadsideWindow
        window = loadsideWindow(self.addon, self)
        self.sortby, self.sortorder = self.sharedproperties.get_sort_options_channels()
        self.recordingfilter = self.sharedproperties.get_recording_filter()
        del window
        self.optionsSelected()

    def showContextMenu(self):
        """
        Should be overriden to receive signal that context menu should popup
        """
        pass

    def optionsSelected(self):
        """
        Should be overriden to receive signal that options were selected
        in the side window
        """
        pass