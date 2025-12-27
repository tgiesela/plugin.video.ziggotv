import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.utils import SharedProperties
from resources.lib.windows.basewindow import baseWindow

class sideWindow(xbmcgui.WindowXMLDialog):
    SIDECHANNELBUTTON=100
    SIDEEPGBUTTON=101
    SIDERECORDINGSBUTTON=102
    SIDEMOVIESBUTTON=103
    LABELSELECTED=9102
    LABELVIEWTYPE=200
    SORTMETHODBUTTON=9301
    SORTMETHODLABEL=9302
    SORTORDERBUTTON=9401
    SORTORDERLABEL=9402
    def __init__(self, xmlFilename, scriptPath, defaultSkin = "Default", defaultRes = "720p", isMedia = False, addon:xbmcaddon.Addon=None,currentWindow=None):
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes, isMedia, addon)
        self.ADDON = addon
        self.currentWindow = currentWindow
        self.sharedproperties = SharedProperties(addon)
        self.sortmethod, self.sortorder = self.sharedproperties.get_sort_options()
        if self.sortorder == '':    
            self.sortorder = SharedProperties.TEXTID_ASCENDING
        if self.sortmethod == '':
            self.sortmethod = SharedProperties.TEXTID_NAME
        self.show()

    def __setlabels(self):
        self.getControl(self.SORTORDERLABEL).setLabel(xbmc.getLocalizedString(int(self.sortorder)))
        self.getControl(self.SORTMETHODLABEL).setLabel(xbmc.getLocalizedString(int(self.sortmethod)))

    def onInit(self):
        self.__setlabels()

    def onAction(self, action):
        super().onAction(action)

    def onClick(self, controlId):
        if controlId in [self.SIDECHANNELBUTTON, self.SIDEEPGBUTTON, self.SIDERECORDINGSBUTTON]:
            self.shortcutClicked(controlId)
            return True
        else:
            if controlId == self.SORTORDERBUTTON:
                if int(self.sortorder) == SharedProperties.TEXTID_DESCENDING:
                    self.sortorder = SharedProperties.TEXTID_ASCENDING
                else:
                    self.sortorder = SharedProperties.TEXTID_DESCENDING
            elif controlId == self.SORTMETHODBUTTON:
                wc = self.currentWindow.__class__.__name__
                if wc in ['channelWindow', 'epgWindow']:
                    if int(self.sortmethod) == SharedProperties.TEXTID_NAME:
                        self.sortmethod = SharedProperties.TEXTID_NUMBER
                    elif int(self.sortmethod) == SharedProperties.TEXTID_NUMBER:
                        self.sortmethod = SharedProperties.TEXTID_NAME
                else:
                    if int(self.sortmethod) == SharedProperties.TEXTID_NAME:
                        self.sortmethod = SharedProperties.TEXTID_NUMBER
                    elif int(self.sortmethod) == SharedProperties.TEXTID_NUMBER:
                        self.sortmethod = SharedProperties.TEXTID_NAME

            self.sharedproperties.set_sort_options(sortby=str(self.sortmethod), sortorder=str(self.sortorder))
            self.__setlabels()
            return True
        
    def onFocus(self, controlId):
        if controlId == self.SIDECHANNELBUTTON:
            sclbl: xbmcgui.ControlLabel = self.getControl(self.LABELSELECTED)
            sclbl.setLabel(xbmc.getLocalizedString(19019))
            return True
        elif controlId == self.SIDEEPGBUTTON:
            selbl: xbmcgui.ControlLabel = self.getControl(self.LABELSELECTED)
            selbl.setLabel(xbmc.getLocalizedString(19069))
            return True
        elif controlId == self.SIDERECORDINGSBUTTON:
            srlbl: xbmcgui.ControlLabel = self.getControl(self.LABELSELECTED)
            srlbl.setLabel(xbmc.getLocalizedString(19017))
            return True
        else:
            return False

    def getSortOptions(self):
        sortbyControl: xbmcgui.ControlButton = self.getControl(self.SORTMETHODBUTTON)
        sortorderControl: xbmcgui.ControlButton = self.getControl(self.SORTORDERBUTTON)
        sortby = sortbyControl.getLabel()
        sortorder = sortorderControl.getLabel()
        return sortby, sortorder
    
    def shortcutClicked(self, controlId):
        if controlId == self.SIDECHANNELBUTTON:
            from resources.lib.windows.channelwindow import loadchannelWindow
            self.close()
            loadchannelWindow(self.ADDON)
        elif controlId == self.SIDEEPGBUTTON:
            from resources.lib.windows.epgwindow import loadepgWindow
            loadepgWindow(self.ADDON)

def loadsideWindow(addon: xbmcaddon.Addon, currentWindow=None):
    CWD: str=addon.getAddonInfo('path')
    sidewindow = sideWindow('sideWindow.xml', CWD, defaultRes='1080i', addon=addon)
    sidewindow.doModal()
    return sidewindow
