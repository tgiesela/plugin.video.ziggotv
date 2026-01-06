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
        self.sortby, self.sortorder = self.sharedproperties.get_sort_options()
        if self.sortby == '' or self.sortorder == '':
            self.sortby = str(SharedProperties.TEXTID_NUMBER)
            self.sortorder = str(SharedProperties.TEXTID_ASCENDING)
            self.sharedproperties.set_sort_options(sortby=self.sortby, sortorder=self.sortorder)

        self.recordingfilter = self.sharedproperties.get_recording_filter()
        if self.recordingfilter == '':    
            self.recordingfilter = str(SharedProperties.TEXTID_RECORDED)
            self.sharedproperties.set_recording_filter(self.recordingfilter)

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
        self.sortby, self.sortorder = self.sharedproperties.get_sort_options()
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