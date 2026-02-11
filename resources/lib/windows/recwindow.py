"""
Module to display window with recordings
"""
from datetime import datetime, timedelta
import threading
import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.channel import ChannelList
from resources.lib.globals import S
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.recording import PlannedRecording, Recording, RecordingList, RecordingType, \
                                    SavedStateList, SeasonRecording, SingleRecording
from resources.lib.utils import ProxyHelper, SharedProperties
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
        self.pos = -1
        self.show()
        self.channels: ChannelList = None
        self.recordings: RecordingList = None
        self.inseason = False
        self.thread: threading.Thread = None
        self.recordingfilter = None
        self.playingListitem = None
        self.recordingtype = RecordingType.RECORDED

    def onInit(self):
        # We will only get recordings the first time we show the window,
        self.recordings = RecordingList(self.addon)
        self.recordings.refresh()
        xbmc.sleep(100)

    def onAction(self, action: xbmcgui.Action):
        listbox: xbmcgui.ControlList = self.getControl(self.LISTBOX)
        # pylint: disable=no-member
        pos = listbox.getSelectedPosition()
        if pos != self.pos:
            li = listbox.getSelectedItem()
            if li is not None:
                self.listitemHelper.update_recording_details(li, self.recordings, self.recordingtype)
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
        self.videoHelper.requestorCallbackStop = self.play_stopped
        self.thread = threading.Thread(target=self.videoHelper.monitor_state,args=(recording.id,))
        self.thread.start()

    def stop_monitor(self):
        """
        Stop the monitoring of the recording
        
        :param self: Description
        """
        if self.thread is not None:
            self.videoHelper.stop_player()
            if self.thread is not None:
                self.thread.join()
                self.thread = None

    def play_stopped(self):
        """
        Method to stop playing, called when the player is stopped, to save the current position of the recording
        Also used as callback for the videoHelper to stop the monitoring when the player is stopped from outside 
        of this window (e.g. from the player itself)
        
        :param self: Description
        """
        self.videoHelper.requestorCallbackStop = None
        if self.playingListitem is not None:
            recording = self.listitemHelper.findrecording(self.playingListitem, self.recordings, self.recordingtype)
            self.listitemHelper.updateresumepointinfo(self.playingListitem,
                                                      recording.id,
                                                      recording.duration)
        self.stop_monitor()

    def __play_recording(self, recording, resumePoint, listitem):
        self.stop_monitor()
        self.playingListitem = listitem
        self.videoHelper.play_recording(recording, resumePoint)
#        self.start_monitor(recording)

    def onClick(self, controlId):
        # pylint: disable=no-member
        super().onClick(controlId)
        if controlId == self.LISTBOX:
            listbox: xbmcgui.ControlList = self.getControl(self.LISTBOX)
            li = listbox.getSelectedItem()
            recording = self.listitemHelper.findrecording(li, self.recordings, self.recordingtype)
            if recording is not None:
                if isinstance(recording, SingleRecording):
                    resumePoint = self.videoHelper.get_resume_point(recording.id)
                    self.__play_recording(recording=recording, resumePoint=resumePoint, listitem=li)
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
        for recording in seasonrecording.get_episodes(self.recordingtype):
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
        self.recordings: RecordingList = RecordingList(self.addon)
        if self.recordingfilter == SharedProperties.TEXTID_RECORDED:
            self.recordingtype = RecordingType.RECORDED
            typelabel.setLabel(f'[B]{self.addon.getLocalizedString(SharedProperties.TEXTID_RECORDED)}[/B]')
        else:
            self.recordingtype = RecordingType.PLANNED
            typelabel.setLabel(f'[B]{self.addon.getLocalizedString(SharedProperties.TEXTID_GEPLAND)}[/B]')

        # Iterate through recordings
        recording: SeasonRecording = None
        for recording in self.recordings.get_season_recordings(self.recordingtype):
            li = self.listitemHelper.listitem_from_recording_season(recording)
            listing.append(li)
        recording: SingleRecording = None
        if self.recordingtype == RecordingType.RECORDED:
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
        li = listbox.getSelectedItem()
        if li is not None:
            self.listitemHelper.update_recording_details(li, self.recordings, self.recordingtype)
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

        recording = self.listitemHelper.findrecording(li, self.recordings, self.recordingtype)
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

        if isinstance(recording, SeasonRecording):
            choices.update({self.addon.getLocalizedString(S.MSG_DELETE_SEASON): 'deleteseason'})

        choices.update({self.addon.getLocalizedString(S.BTN_CANCEL): 'cancel'})
        choicesList = list(choices.keys())
        selected = xbmcgui.Dialog().contextmenu(choicesList)

        action = choices[choicesList[selected]]
        if action == 'playbeginning':
            self.__play_recording(recording, resumePoint, li)
        elif action == 'resume':
            self.__play_recording(recording, resumePoint, li)
        elif action == 'delete':
            self.recordings.delete_recording(recording)
            listctrl.removeItem(listctrl.getSelectedPosition())
            self.recordings.refresh()
            xbmcgui.Dialog().notification('Info',
                                          self.addon.getLocalizedString(S.MSG_DELETE_RECORDING_COMPLETE),
                                          xbmcgui.NOTIFICATION_INFO,
                                          2000)
        elif action == 'deleteseason':
            delallchoice = xbmcgui.Dialog().yesno('Delete',
                                                   self.addon.getLocalizedString(S.MSG_DELETE_SEASON_ALL))
            self.recordings.delete_season_recording(recording, delallchoice)
            listctrl.removeItem(listctrl.getSelectedPosition())
            self.recordings.refresh()
            xbmcgui.Dialog().notification('Info',
                                    self.addon.getLocalizedString(S.MSG_DELETE_SEASON_COMPLETE),
                                    xbmcgui.NOTIFICATION_INFO,
                                    2000)
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
