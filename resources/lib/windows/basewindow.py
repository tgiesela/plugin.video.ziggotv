import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.windows.sidewindow import loadsideWindow

class baseWindow(xbmcgui.WindowXML):
    OPTIONICON=9001
    OPTIONLABEL=9002
    def __init__(self, xmlFilename, scriptPath, defaultSkin = "Default", defaultRes = "720p", isMedia = False, addon: xbmcaddon.Addon=None):
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes, isMedia)
        self.addon = addon
        self.sidewindow = loadsideWindow(self.addon, self)

    def onAction(self, action):
        if action.getId() == xbmcgui.ACTION_STOP:
            xbmc.log(f'Window onAction STOP', xbmc.LOGDEBUG)
            return

        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU or action.getId() == xbmcgui.ACTION_NAV_BACK:
            xbmc.log(f'Window onAction PREVIOUS or BACK', xbmc.LOGDEBUG)
            return

        super().onAction(action)

    def onClick(self, controlId):
        if controlId in [self.OPTIONICON,self.OPTIONLABEL]:
            xbmc.log(f'Window OPTION Icon', xbmc.LOGDEBUG)
            self.showOptions()
            return
        if not self.sidewindow.onClick(controlId):
            if controlId == self.CHANNELBUTTON:
                from resources.lib.windows.channelwindow import loadchannelWindow
                loadchannelWindow(self.addon)
            elif controlId == self.EPGBUTTON:
                loadepgWindow(self.addon)
            else:
                super().onClick(controlId)

    def onFocus(self, controlId):
        if self.sidewindow.onFocus(controlId):
            return True
        return super().onFocus(controlId)

    def showOptions(self):
        self.sidewindow.window.doModal()
        sortby, sortorder = self.sidewindow.getSortOptions()
