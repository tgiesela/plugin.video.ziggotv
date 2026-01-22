"""
Module to display window with recordings
"""
from datetime import datetime, timedelta
import threading
import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.channel import ChannelList, SavedChannelsList
from resources.lib.globals import S
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.recording import PlannedRecording, Recording, RecordingList, SavedStateList, SeasonRecording, SingleRecording
from resources.lib.utils import ProxyHelper, SharedProperties
from resources.lib.videohelpers import VideoHelpers
from resources.lib.webcalls import LoginSession
from resources.lib.windows.basewindow import BaseWindow

class RecordingWindow(BaseWindow):
    """
    class for recording window which show planned and recorded recordings
    """
    LISTBOX = 50
    RECTYPELABEL = 51
    def __init__(self, xmlFilename, scriptPath, defaultSkin = "Default", defaultRes = "720p",
                 isMedia = False, addon:xbmcaddon.Addon=None):
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes, isMedia, addon)
        self.addon = addon
        self.helper = ProxyHelper(self.addon)
        self.listitemHelper = ListitemHelper(self.addon)
        self.videoHelper = VideoHelpers(self.addon)
        self.pos = -1
        self.show()
        self.channels: ChannelList = None
        self.savedchannelslist = SavedChannelsList(self.addon)
        self.recordings: RecordingList = None
        self.inseason = False
        self.thread: threading.Thread = None
        self.recordingfilter = None

    def onInit(self):
        xbmc.sleep(100)

    def onAction(self, action: xbmcgui.Action):
        listbox: xbmcgui.ControlList = self.getControl(self.LISTBOX)
        # pylint: disable=no-member
        pos = listbox.getSelectedPosition()
        if pos != self.pos:
            self.listitemHelper.update_recording_details(listbox.getSelectedItem(), self.recordings, self.recordingfilter)
            self.pos = pos

        if action.getId() == xbmcgui.ACTION_STOP:
            xbmc.log('Window onAction STOP', xbmc.LOGDEBUG)
            return

        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU or action.getId() == xbmcgui.ACTION_NAV_BACK:
            xbmc.log('Window onAction PREVIOUS or BACK', xbmc.LOGDEBUG)
            if self.inseason:
                self.showrecordings()
                return
        super().onAction(action)

    def start_monitor(self, recording:SingleRecording):
        """
        Function to start monitoring a playing recording to capture the current position.
        
        :param self: 
        :param recording: the recording to monitor
        :type recording: SingleRecording
        """
        self.thread = threading.Thread(target=self.videoHelper.monitor_state,args=(recording.id,))
        self.thread.start()

    def stop_monitor(self):
        """
        Stop the monitoring of the recording
        
        :param self: Description
        """
        if self.thread is not None:
            self.videoHelper.stop_player()
            self.thread.join()
            self.thread = None

    def onClick(self, controlId):
        # pylint: disable=no-member
        super().onClick(controlId)
        if controlId == self.LISTBOX:
            listbox: xbmcgui.ControlList = self.getControl(self.LISTBOX)
            li = listbox.getSelectedItem()
            recording = self.listitemHelper.findrecording(li, self.recordings, self.recordingfilter)
            if recording is not None:
                if isinstance(recording, SingleRecording):
                    self.videoHelper = VideoHelpers(self.addon)
                    resumePoint = self.videoHelper.get_resume_point(recording.id)
                    self.stop_monitor()
                    self.videoHelper.play_recording(recording, resumePoint)
                    self.start_monitor(recording)
                elif isinstance(recording, SeasonRecording):
                    self.showseasonrecordings(recording)

    def options_selected(self):
        """
        called when options were selected in the side window
        """
        self.showrecordings()

    def showseasonrecordings(self, seasonrecording: SeasonRecording):
        """
        method to show all episodes in a season recording
        """
        self.inseason = True
        self.pos = -1
        listbox: xbmcgui.ControlList = self.getControl(self.LISTBOX) # Fixedlist
        # pylint: disable=no-member
        # Create a list for our items.
        listbox.reset()
        listing = []

        # Iterate through recordings
        recording: Recording = None
        if self.recordingfilter == SharedProperties.TEXTID_RECORDED:
            rectype = 'recorded' # 40032
        else:
            rectype = 'planned'
        for recording in seasonrecording.get_episodes(rectype):
#            rec = self.__findrecording(recording.id)
            li = self.listitemHelper.listitem_from_recording(recording)
            listing.append(li)
        
        # Apply sorting
        sortby, sortorder = self.sharedproperties.get_sort_options_recordings()
        self.recordings.sort_listitems(listing, sortby, sortorder)
        listbox.addItems(listing)
        listbox.selectItem(0)
        self.setFocusId(self.LISTBOX)

    def showrecordings(self):
        """
        method to show recordings
        
        :param self: 
        """
        self.recordingfilter = int(self.sharedproperties.get_recording_filter())
        self.inseason = False
        self.pos = -1
        listbox: xbmcgui.ControlList = self.getControl(self.LISTBOX) # Fixedlist
        typelabel: xbmcgui.ControlLabel = self.getControl(self.RECTYPELABEL)
        # pylint: disable=no-member

        # Create a list for our items.
        listbox.reset()
        listing = []
        self.helper.dynamic_call(LoginSession.refresh_recordings,
                                 includeAdult=self.addon.getSettingBool('adult-allowed'))
        if self.recordingfilter == SharedProperties.TEXTID_RECORDED:
            self.recordings: RecordingList = self.helper.dynamic_call(LoginSession.get_recordings_recorded)
            typelabel.setLabel(f'[B]{self.addon.getLocalizedString(SharedProperties.TEXTID_RECORDED)}[/B]')
        else:
            self.recordings: RecordingList = self.helper.dynamic_call(LoginSession.get_recordings_planned)
            typelabel.setLabel(f'[B]{self.addon.getLocalizedString(SharedProperties.TEXTID_GEPLAND)}[/B]')

        # Iterate through recoordings
        recording: SeasonRecording = None
        for recording in self.recordings.get_season_recordings():
            li = self.listitemHelper.listitem_from_recording_season(recording)
            listing.append(li)
        recording: SingleRecording = None
        if self.recordingfilter == SharedProperties.TEXTID_RECORDED:
            for recording in self.recordings.get_recorded_recordings():
                if isinstance(recording, (SingleRecording)):
                    li = self.listitemHelper.listitem_from_recording(recording)
                    listing.append(li)
        else:
            for recording in self.recordings.get_planned_recordings():
                if isinstance(recording, (PlannedRecording)):
                    li = self.listitemHelper.listitem_from_recording(recording)
                    listing.append(li)

        # Apply sorting
        sortby, sortorder = self.sharedproperties.get_sort_options_recordings()
        self.recordings.sort_listitems(listing, sortby, sortorder)
        listbox.addItems(listing)
        listbox.selectItem(0)
        self.listitemHelper.update_recording_details(listbox.getSelectedItem(), self.recordings, self.recordingfilter)
        self.setFocusId(self.LISTBOX)

    def show_context_menu(self):
        listctrl: xbmcgui.ControlList = self.getControl(self.LISTBOX)
        # pylint: disable=no-member
        li: xbmcgui.ListItem = listctrl.getSelectedItem()
        if li is None:
            return
        if li.getProperty('isDeleted') == 'true':
            return
        # Which actions can be added depends on type of current selected item
        #
        #  1:   SingleRecording
        #       play, resume, delete, deleteseason (if applicable)
        #  2:   PlannedRecording
        #       delete, deleteseason (if applicable)
        #  3:   SeasonRecording (Planned/recorded)
        #       deleteseason (if applicable)

        recording = self.listitemHelper.findrecording(li, self.recordings, self.recordingfilter)
        if recording is None:
            xbmc.log('Recording not found while processing context menu', xbmc.LOGDEBUG)
            return

        resumePoint = 0

        choices = {}
        if isinstance(recording, SingleRecording):
            choices = {self.addon.getLocalizedString(S.MSG_PLAY_FROM_BEGINNING): 'playbeginning'}
            savedstateList = SavedStateList(self.addon)
            resumePoint = savedstateList.get(recording.id)
            if resumePoint is not None:
                t = datetime.now().replace(hour=0, minute=0, second=0) + timedelta(seconds=resumePoint)
                choices.update({self.addon.getLocalizedString(
                    S.MSG_RESUME_FROM).format(t.strftime('%H:%M:%S')): 'resume'})

        choices.update({self.addon.getLocalizedString(S.MSG_DELETE): 'delete'})

        if isinstance(recording, SeasonRecording) or recording.showId is not None:
            choices.update({self.addon.getLocalizedString(S.MSG_DELETE_SEASON): 'deleteseason'})

        choices.update({self.addon.getLocalizedString(S.BTN_CANCEL): 'cancel'})
        choicesList = list(choices.keys())
        selected = xbmcgui.Dialog().contextmenu(choicesList)

        action = choices[choicesList[selected]]
        if action == 'playbeginning':
            self.videoHelper.play_recording(recording, resumePoint)
        elif action == 'resume':
            self.videoHelper.play_recording(recording, resumePoint)
        elif action == 'delete':
            if self.recordingfilter == SharedProperties.TEXTID_GEPLAND:
                self.helper.dynamic_call(LoginSession.delete_recordings_planned,
                                    event=recording.id,
                                    show=None,
                                    channelId=recording.channelId)
            else:
                self.helper.dynamic_call(LoginSession.delete_recordings,
                                    event=recording.id,
                                    show=None,
                                    channelId=recording.channelId)
            li.setLabel(f'[COLOR red]{li.getLabel()}[/COLOR]')
            li.setProperty('isDeleted', 'true')
            xbmcgui.Dialog().notification('Info',
                                          self.addon.getLocalizedString(S.MSG_DELETE_RECORDING_COMPLETE),
                                          xbmcgui.NOTIFICATION_INFO,
                                          2000)
            xbmc.log("Recording with id {0} deleted".format(id), xbmc.LOGDEBUG)
        elif action == 'deleteseason':
            if recording.showId is not None:
                if self.recordingfilter == SharedProperties.TEXTID_GEPLAND:
                    self.helper.dynamic_call(LoginSession.delete_recordings_planned,
                                        show=recording.showId,
                                        channelId=recording.channelId)
                else:
                    self.helper.dynamic_call(LoginSession.delete_recordings,
                                        show=recording.showId,
                                        channelId=recording.channelId)
                li.setLabel(f'[COLOR red]{li.getLabel()}[/COLOR]')
                li.setProperty('isDeleted', 'true')
                xbmcgui.Dialog().notification('Info',
                                      self.addon.getLocalizedString(S.MSG_DELETE_SEASON_COMPLETE),
                                      xbmcgui.NOTIFICATION_INFO,
                                      2000)
                xbmc.log("Recording of complete show with id {0} deleted".format(recording.showId), xbmc.LOGDEBUG)
        elif action == 'cancel':
            pass

def load_recordingwindow(addon:xbmcaddon.Addon):
    """
    Function to create, populate and display the recording form
    
    :param addon: the addon for which the form is created
    :type addon: xbmcaddon.Addon
    """
    cwd: str=addon.getAddonInfo('path')
    recwindow = RecordingWindow('recordings.xml', cwd, defaultRes='1080i',addon=addon)
    recwindow.showrecordings()
    recwindow.doModal()
    recwindow.stop_monitor() # make sure thread is stopped at the end
    del recwindow
