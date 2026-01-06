import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.channel import SavedChannelsList
from resources.lib.recording import SavedStateList
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
    FILTERBUTTON=9501
    FILTERLABEL=9502
    CLEARDATABUTTON=9601
    CLEARDATALABEL=9602
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
        self.recordingfilter = self.sharedproperties.get_recording_filter()
        if self.recordingfilter == '':    
            self.recordingfilter = str(SharedProperties.TEXTID_RECORDED)  # All Recordings with state "Recorded"
        self.show()

    def __setlabels(self):
        self.getControl(self.SORTORDERLABEL).setLabel(xbmc.getLocalizedString(int(self.sortorder)))
        self.getControl(self.SORTMETHODLABEL).setLabel(xbmc.getLocalizedString(int(self.sortmethod)))
        self.getControl(self.FILTERLABEL).setLabel(self.ADDON.getLocalizedString(int(self.recordingfilter)))
        wc = self.currentWindow.__class__.__name__
        xbmc.log(f'Side Window current window class: {wc}', xbmc.LOGINFO)
        self.getControl(self.FILTERBUTTON).setVisible(False)
        self.getControl(self.FILTERLABEL).setVisible(False)
        if wc.lower() in ['channelwindow', 'epgwindow', 'homewindow']:
            if int(self.sortmethod) not in [SharedProperties.TEXTID_NAME, SharedProperties.TEXTID_NUMBER]:
                self.sortmethod = SharedProperties.TEXTID_NAME
        if wc.lower() == 'recordingwindow':
            self.getControl(self.SIDERECORDINGSBUTTON).setEnabled(False)
            self.getControl(self.FILTERBUTTON).setVisible(True)
            self.getControl(self.FILTERLABEL).setVisible(True)
        elif wc.lower() == 'channelwindow':
            self.getControl(self.SIDECHANNELBUTTON).setEnabled(False)
        elif wc.lower() == 'epgwindow':
            self.getControl(self.SIDEEPGBUTTON).setEnabled(False)

    def onInit(self):
        xbmc.sleep(100)
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
                if wc.lower() in ['channelwindow', 'epgwindow']:
                    if int(self.sortmethod) == SharedProperties.TEXTID_NAME:
                        self.sortmethod = SharedProperties.TEXTID_NUMBER
                    elif int(self.sortmethod) == SharedProperties.TEXTID_NUMBER:
                        self.sortmethod = SharedProperties.TEXTID_NAME
                elif wc.lower() == 'recordingwindow':
                    if int(self.sortmethod) == SharedProperties.TEXTID_NAME:
                        self.sortmethod = SharedProperties.TEXTID_DATE
                    elif int(self.sortmethod) == SharedProperties.TEXTID_NUMBER:
                        self.sortmethod = SharedProperties.TEXTID_DATE
                    elif int(self.sortmethod) == SharedProperties.TEXTID_DATE:
                        self.sortmethod = SharedProperties.TEXTID_NAME
            elif controlId == self.FILTERBUTTON:
                if int(self.recordingfilter) == SharedProperties.TEXTID_RECORDED:
                    self.recordingfilter = SharedProperties.TEXTID_GEPLAND
                else:
                    self.recordingfilter = SharedProperties.TEXTID_RECORDED
            elif controlId == self.CLEARDATABUTTON:
                SavedStateList(self.ADDON).cleanup(0)
                SavedChannelsList(self.ADDON).cleanup(0)
                self.close()
                return

            self.sharedproperties.set_sort_options(sortby=str(self.sortmethod), sortorder=str(self.sortorder))
            self.sharedproperties.set_recording_filter(str(self.recordingfilter))
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
            self.close()
            loadepgWindow(self.ADDON)
        elif controlId == self.SIDERECORDINGSBUTTON:
            from resources.lib.windows.recwindow import loadrecordingWindow
            self.close()
            loadrecordingWindow(self.ADDON)

def loadsideWindow(addon: xbmcaddon.Addon, currentWindow=None):
    CWD: str=addon.getAddonInfo('path')
    sidewindow = sideWindow('sideWindow.xml', CWD, defaultRes='1080i', addon=addon, currentWindow=currentWindow)
    sidewindow.doModal()
    return sidewindow
