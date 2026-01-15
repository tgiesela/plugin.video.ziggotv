"""
Module containing all logic for the sidewindow (options)
It is not as clean as should, but all logic is in here.
For cleanup the calling window should have a method named 'cleanup'
"""
import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.channel import SavedChannelsList
from resources.lib.recording import SavedStateList
from resources.lib.utils import SharedProperties

class SideWindow(xbmcgui.WindowXMLDialog):
    """
    class for display the side window with sort/filter options
    """
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
    def __init__(self, xmlFilename, scriptPath, defaultSkin = "Default",
                 defaultRes = "720p", isMedia = False, addon:xbmcaddon.Addon=None,currentWindow=None):
        # pylint: disable=too-many-function-args
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes, isMedia, addon)
        self.sortoptions = {}
        self.allowedsortmethods = {'channel': [SharedProperties.TEXTID_NAME, SharedProperties.TEXTID_NUMBER],
                                   'recording': [SharedProperties.TEXTID_NAME, SharedProperties.TEXTID_DATE],
                                   'movies': [SharedProperties.TEXTID_NAME]}
        self.addon = addon
        self.currentWindow = currentWindow
        self.sharedproperties = SharedProperties(addon)
        self.__get_sort_options()
        self.recordingfilter = self.sharedproperties.get_recording_filter()
        if self.recordingfilter == '':
            self.recordingfilter = str(SharedProperties.TEXTID_RECORDED)  # All Recordings with state "Recorded"
        self.show()

    def __get_sort_options(self):
        sortmethod, sortorder = self.sharedproperties.get_sort_options_channels()
        if sortorder == '':
            sortorder = SharedProperties.TEXTID_ASCENDING
        if sortmethod == '':
            sortmethod = SharedProperties.TEXTID_NAME
        self.sortoptions.update({'channel': {'method': sortmethod, 'order': sortorder}})

        sortmethod, sortorder = self.sharedproperties.get_sort_options_recordings()
        if sortorder == '':
            sortorder = SharedProperties.TEXTID_ASCENDING
        if sortmethod == '':
            sortmethod = SharedProperties.TEXTID_NAME
        self.sortoptions.update({'recording': {'method': sortmethod, 'order': sortorder}})

        sortmethod, sortorder = self.sharedproperties.get_sort_options_movies()
        if sortorder == '':
            sortorder = SharedProperties.TEXTID_ASCENDING
        if sortmethod == '':
            sortmethod = SharedProperties.TEXTID_NAME
        self.sortoptions.update({'movies': {'method': sortmethod, 'order': sortorder}})

    def __next_sort_order(self):
        wc = self.currentWindow.__class__.__name__
        if wc.lower() == 'recordingwindow':
            options = self.sortoptions['recording']
        elif wc.lower() in ['channelwindow','epgwindow','homewindow']:
            options = self.sortoptions['channel']
        elif wc.lower() == 'moviewindow':
            options = self.sortoptions['movies']
        else:
            return
        if int(options['order']) == SharedProperties.TEXTID_DESCENDING:
            options['order'] = SharedProperties.TEXTID_ASCENDING
        else:
            options['order'] = SharedProperties.TEXTID_DESCENDING
        if wc.lower() == 'recordingwindow':
            self.sharedproperties.set_sort_options_recordings(sortby=str(options['method']),
                                                              sortorder=str(options['order']))
        elif wc.lower() in ['channelwindow','epgwindow','homewindow']:
            self.sharedproperties.set_sort_options_channels(sortby=str(options['method']),
                                                            sortorder=str(options['order']))
        elif wc.lower() == 'moviewindow':
            self.sharedproperties.set_sort_options_movies(sortby=str(options['method']),
                                                          sortorder=str(options['order']))

    def __next_sort_method(self):
        wc = self.currentWindow.__class__.__name__
        if wc.lower() == 'recordingwindow':
            options = self.sortoptions['recording']
            allowed = self.allowedsortmethods['recording']
        elif wc.lower() in ['channelwindow','epgwindow','homewindow']:
            options = self.sortoptions['channel']
            allowed = self.allowedsortmethods['channel']
        elif wc.lower() == 'moviewindow':
            options = self.sortoptions['movies']
            allowed = self.allowedsortmethods['movies']
        else:
            return
        xbmc.log(f"OPTIONS {options}, ALLOWED {allowed}, current {options['method']}", xbmc.LOGINFO)
        currentindex = allowed.index(int(options['method']))
        currentindex += 1
        if currentindex >= len(allowed):
            currentindex = 0

        options['method'] = allowed[currentindex]

        if wc.lower() == 'recordingwindow':
            self.sharedproperties.set_sort_options_recordings(sortby=str(options['method']),
                                                              sortorder=str(options['order']))
        elif wc.lower() in ['channelwindow','epgwindow','homewindow']:
            self.sharedproperties.set_sort_options_channels(sortby=str(options['method']),
                                                            sortorder=str(options['order']))
        elif wc.lower() == 'moviewindow':
            self.sharedproperties.set_sort_options_movies(sortby=str(options['method']),
                                                          sortorder=str(options['order']))

    def __setlabels(self):
        wc = self.currentWindow.__class__.__name__
        if wc.lower() == 'recordingwindow':
            options = self.sortoptions['recording']
        elif wc.lower() in ['channelwindow','epgwindow','homewindow']:
            options = self.sortoptions['channel']
        elif wc.lower() == 'moviewindow':
            options = self.sortoptions['movies']
        else:
            options = {}
        # pylint: disable=no-member
        self.getControl(self.SORTORDERLABEL).setLabel(xbmc.getLocalizedString(int(options['order'])))
        self.getControl(self.SORTMETHODLABEL).setLabel(xbmc.getLocalizedString(int(options['method'])))
        self.getControl(self.FILTERLABEL).setLabel(self.addon.getLocalizedString(int(self.recordingfilter)))
        wc = self.currentWindow.__class__.__name__
        xbmc.log(f'Side Window current window class: {wc}', xbmc.LOGINFO)
        self.getControl(self.FILTERBUTTON).setVisible(False)
        self.getControl(self.FILTERLABEL).setVisible(False)
        if wc.lower() == 'recordingwindow':
            self.getControl(self.SIDERECORDINGSBUTTON).setEnabled(False)
            self.getControl(self.FILTERBUTTON).setVisible(True)
            self.getControl(self.FILTERLABEL).setVisible(True)
        elif wc.lower() == 'channelwindow':
            self.getControl(self.SIDECHANNELBUTTON).setEnabled(False)
        elif wc.lower() == 'epgwindow':
            self.getControl(self.SIDEEPGBUTTON).setEnabled(False)
        elif wc.lower() == 'moviewindow':
            self.getControl(self.SIDEMOVIESBUTTON).setEnabled(False)

    def onInit(self):
        xbmc.sleep(100)
        self.__setlabels()

    def onAction(self, action):
        # pylint: disable=useless-parent-delegation
        super().onAction(action)

    def onClick(self, controlId):
        if controlId in [self.SIDECHANNELBUTTON, self.SIDEEPGBUTTON, self.SIDERECORDINGSBUTTON]:
            self.shortcut_clicked(controlId)
            return True
        else:
            if controlId == self.SORTORDERBUTTON:
                self.__next_sort_order()
            elif controlId == self.SORTMETHODBUTTON:
                self.__next_sort_method()
            elif controlId == self.FILTERBUTTON:
                if int(self.recordingfilter) == SharedProperties.TEXTID_RECORDED:
                    self.recordingfilter = SharedProperties.TEXTID_GEPLAND
                else:
                    self.recordingfilter = SharedProperties.TEXTID_RECORDED
            elif controlId == self.CLEARDATABUTTON:
                SavedStateList(self.addon).cleanup(0)
                SavedChannelsList(self.addon).cleanup(0)

                cleanupMethod = getattr(self.currentWindow, "cleanup", None)
                if cleanupMethod is not None and callable(cleanupMethod):
                    self.currentWindow.cleanup()
                self.close()
                return

            self.sharedproperties.set_recording_filter(str(self.recordingfilter))
            self.__setlabels()
            return True

    def onFocus(self, controlId):
        # pylint: disable=no-member
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
        elif controlId == self.SIDEMOVIESBUTTON:
            srlbl: xbmcgui.ControlLabel = self.getControl(self.LABELSELECTED)
            srlbl.setLabel(xbmc.getLocalizedString(342))
            return True
        else:
            return False

    def shortcut_clicked(self, controlId):
        """
        Function to handle click on the shortcuts
        
        :param self: 
        :param controlId: the id of the clicked control
        """
        if controlId == self.SIDECHANNELBUTTON:
            # pylint: disable=import-outside-toplevel
            from resources.lib.windows.channelwindow import load_channelwindow
            self.close()
            load_channelwindow(self.addon)
        elif controlId == self.SIDEEPGBUTTON:
            # pylint: disable=import-outside-toplevel
            from resources.lib.windows.epgwindow import load_epgwindow
            self.close()
            load_epgwindow(self.addon)
        elif controlId == self.SIDERECORDINGSBUTTON:
            # pylint: disable=import-outside-toplevel
            from resources.lib.windows.recwindow import load_recordingwindow
            self.close()
            load_recordingwindow(self.addon)
        elif controlId == self.SIDEMOVIESBUTTON:
            # pylint: disable=import-outside-toplevel
            from resources.lib.windows.moviewindow import load_moviewindow
            self.close()
            load_moviewindow(self.addon)

def load_sidewindow(addon: xbmcaddon.Addon, currentWindow=None):
    """
    Function to create, populate and display the sidewindow
    
    :param addon: the addon for which the form is created
    :type addon: xbmcaddon.Addon
    """
    cwd: str=addon.getAddonInfo('path')
    sidewindow = SideWindow('sidewindow.xml', cwd, defaultRes='1080i', addon=addon, currentWindow=currentWindow)
    sidewindow.doModal()
    return sidewindow
