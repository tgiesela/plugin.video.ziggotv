import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.utils import SharedProperties

class sideWindow():
    SIDECHANNELBUTTON=100
    SIDEEPGBUTTON=101
    SIDERECORDINGSBUTTON=102
    SIDEMOVIESBUTTON=103
    LABELSELECTED=60522
    LABELVIEWTYPE=200
    SORTMETHODBUTTON=6053
    SORTORDERBUTTON=6055
    def __init__(self, addon: xbmcaddon.Addon, currentWindow=None):
        self.window = xbmcgui.WindowXMLDialog('sidewindow.xml', addon.getAddonInfo('path'), defaultRes='1080i', isMedia=False)
        self.addon = addon
        self.currentWindow = currentWindow
        self.sharedproperties = SharedProperties(addon)
        self.onInit()

    def onInit(self):
        xbmc.log(f'SideWindow onInit', xbmc.LOGINFO)

        sortorder, sortmethod = self.sharedproperties.get_sort_options()
        self.window.getControl(self.SORTMETHODBUTTON).setLabel(sortmethod)
        self.window.getControl(self.SORTORDERBUTTON).setLabel(sortorder)

    def onAction(self, action):
        pass

    def onClick(self, controlId):
        if controlId in [self.SIDECHANNELBUTTON, self.SIDEEPGBUTTON, self.SIDERECORDINGSBUTTON]:
            self.shortcutClicked(controlId)
            return True
        else:
            if controlId == self.SORTORDERBUTTON:
                if self.window.getControl(self.SORTORDERBUTTON).getLabel() == 'Ascending':
                    sortorder = 'Descending'
                else:
                    sortorder = 'Ascending'
                self.sharedproperties.set_sort_options(sortorder=sortorder)
                return True
            return False
        
    def onFocus(self, controlId):
        if controlId == self.SIDECHANNELBUTTON:
            self.window.getControl(self.LABELSELECTED).setLabel(self.addon.getLocalizedString(40010))
            return True
        elif controlId == self.SIDEEPGBUTTON:
            self.window.getControl(self.LABELSELECTED).setLabel(self.addon.getLocalizedString(40011))
            return True
        elif controlId == self.SIDERECORDINGSBUTTON:
            self.window.getControl(self.LABELSELECTED).setLabel(self.addon.getLocalizedString(40015))
            return True
        else:
            return False

    def show(self):
        self.window.show()
        if self.currentWindow.__class__.__name__ == "homeWindow":
            self.onInit()
        elif self.currentWindow.__class__.__name__ == "channelWindow":
#            self.window.getControl(self.SIDECHANNELBUTTON).setEnabled(False)
            self.onInit()

    def getSortOptions(self):
        sortbyControl: xbmcgui.ControlButton = self.window.getControl(self.SORTMETHODBUTTON)
        sortorderControl: xbmcgui.ControlButton = self.window.getControl(self.SORTORDERBUTTON)
        sortby = sortbyControl.getLabel()
        sortorder = sortorderControl.getLabel()
        return sortby, sortorder
    
    def shortcutClicked(self, controlId):
        if controlId == self.SIDECHANNELBUTTON:
            from resources.lib.windows.channelwindow import loadchannelWindow
            loadchannelWindow(self.addon)
        elif controlId == self.SIDEEPGBUTTON:
            from resources.lib.windows.epgwindow import loadepgWindow
            loadepgWindow(self.addon)

def loadsideWindow(addon: xbmcaddon.Addon, currentWindow=None):
    CWD: str=addon.getAddonInfo('path')
    sidewindow = sideWindow(addon, currentWindow)
    return sidewindow

