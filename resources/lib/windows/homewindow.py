import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.windows.basewindow import baseWindow
from resources.lib.windows.channelwindow import loadchannelWindow
class homeWindow(baseWindow):
    GROUPLIST=50
    CHANNELBUTTON=5
    EPGBUTTON=6
    RECORDINGSBUTTON=7
    MOVIESBUTTON=8
    def __init__(self, xmlFilename, scriptPath, defaultSkin = "Default", defaultRes = "720p", isMedia = False, addon=''):
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes, isMedia, addon)
        self.addon = addon
    
    def onInit(self):
        # give kodi a bit of (processing) time to add all items to the container
        xbmc.sleep(100)
        # this puts the focus on the first button of the screen
        self.setFocusId(5)

    def onFocus(self, controlId):
        if self.sidewindow.onFocus(controlId):
            return True
        super().onFocus(controlId)
    
    def onAction(self, action):
        super().onAction(action)
        if action.getId() == xbmcgui.ACTION_STOP:
            xbmc.log(f'Window onAction STOP', xbmc.LOGDEBUG)
            self.close()
            return

        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU or action.getId() == xbmcgui.ACTION_NAV_BACK:
            xbmc.log(f'Window onAction PREVIOUS or BACK', xbmc.LOGDEBUG)
            self.close()
            return

    def onClick(self, controlId):
        super().onClick(controlId)
        if controlId == self.CHANNELBUTTON:
            loadchannelWindow(self.addon)
        elif controlId == self.EPGBUTTON:
            pass


def loadhomeWindow(addon: xbmcaddon.Addon):
    window = homeWindow('ziggohome.xml', addon.getAddonInfo('path'), defaultRes='1080i', addon=addon)
    window.doModal()

    
