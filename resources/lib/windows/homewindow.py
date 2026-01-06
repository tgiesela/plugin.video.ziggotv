import time
import xbmc
import xbmcgui
import xbmcaddon

from resources.lib import utils
from resources.lib.channel import Channel, ChannelList, SavedChannelsList
from resources.lib.channelguide import ChannelGuide
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.recording import Recording, RecordingList, SeasonRecording
from resources.lib.utils import KeyMapMonitor, ProxyHelper, check_service
from resources.lib.videohelpers import VideoHelpers
from resources.lib.webcalls import LoginSession
from resources.lib.windows.basewindow import baseWindow
from resources.lib.windows.channelwindow import loadchannelWindow
from resources.lib.windows.epgwindow import loadepgWindow
from resources.lib.windows.moviewindow import loadmovieWindow
from resources.lib.windows.recwindow import loadrecordingWindow
class homeWindow(baseWindow):
    GROUPLIST=50
    CHANNELBUTTON=5
    EPGBUTTON=6
    RECORDINGSBUTTON=7
    MOVIESBUTTON=8
    RECENTCHANNELLIST=150
    RECENTRECORDINGSLIST=250
    def __init__(self, xmlFilename, scriptPath, defaultSkin = "Default", defaultRes = "720p", isMedia = False, addon=''):
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes, isMedia, addon)
        self.ADDON = addon
        self.savedchannelslist = None
        self.recentchannels = None
        self.helper = ProxyHelper(self.ADDON)
        self.channels = self.helper.dynamic_call(LoginSession.get_channels)
        self.listitemHelper = ListitemHelper(self.ADDON)
        self.videoHelper = VideoHelpers(self.ADDON)
        self.keyboardmonitor = KeyMapMonitor(self.ADDON, self.switchToChannel)
    
    def __del__(self):
        self.keyboardmonitor = None

    def __findchannel(self,id):
        channel: Channel = None
        for channel in self.channels:
            if id == channel.id:
                return channel
        return None   

    def __findchannel_by_number(self,number):
        channel: Channel = None
        for channel in self.channels:
            if int(number) == channel.logicalChannelNumber:
                return channel
        return None   

    def __do_play_channel(self, channel: Channel):
        self.videoHelper.play_channel(channel=channel)
        if channel is not None:
            self.savedchannelslist.add(channel.id, channel.name)

    def __showrecentchannels(self):
        self.savedchannelslist = SavedChannelsList(self.ADDON)
        self.recentchannels = self.savedchannelslist.getAll()
        listing = []
        # this puts the focus on the first button of the screen
        recentchannellist: xbmcgui.ControlList = self.getControl(self.RECENTCHANNELLIST)
        entitlements = self.helper.dynamic_call(LoginSession.get_entitlements)
        channelList = ChannelList(self.channels, entitlements)
        channelList.entitledOnly = self.ADDON.getSettingBool('allowed-channels-only')
        channelList.apply_filter()
        # Obtain events

        self.listitemHelper.channelList = channelList
        self.listitemHelper.refreshepg()

        recentchannellist.reset()

        for recentchannel in self.recentchannels:
#            channelname = self.recentchannels[recentchannel]['name']
            channelobj:Channel = self.__findchannel(recentchannel)
            if channelobj is None:
                continue
            li = self.listitemHelper.listitem_from_channel(channelobj)
#            li.setProperty('IsPlayable', 'false')  # Turn off to avoid kodi complaining about item not playing
            listing.append(li)

        recentchannellist.addItems(listing)
        recentchannellist.selectItem(0)
        self.setFocusId(5)
    
    def switchToChannel(self, newchannel: str):
        channel = self.__findchannel_by_number(newchannel)
        if channel is None:
            xbmc.executebuiltin(f'Notification(Channel,{self.keypresses} not found)')
            return
        self.__do_play_channel(channel)

    def onInit(self):
        # give kodi a bit of (processing) time to add all items to the container
        xbmc.sleep(100)
        self.__showrecentchannels()
        # self.__showrecentrecordings()

    def onFocus(self, controlId):
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
            loadchannelWindow(self.ADDON)
        elif controlId == self.EPGBUTTON:
            loadepgWindow(self.ADDON)
        elif controlId == self.RECORDINGSBUTTON:
            loadrecordingWindow(self.ADDON)
        elif controlId == self.MOVIESBUTTON:
            loadmovieWindow(self.ADDON)
        elif controlId == self.RECENTCHANNELLIST:
            list: xbmcgui.ControlList = self.getControl(self.RECENTCHANNELLIST)
            li = list.getSelectedItem()
            channel = self.listitemHelper.findchannel(li, self.channels)
            if channel is not None:
                self.__do_play_channel(channel=channel)
            else:
                xbmc.log(f'Channel not found for listitem {li.getLabel()}', xbmc.LOGERROR)

def loadhomeWindow(addon: xbmcaddon.Addon):
    from resources.lib.utils import invoke_debugger
    invoke_debugger(True, 'vscode')
    check_service(addon)
    window = homeWindow('ziggohome.xml', addon.getAddonInfo('path'), defaultRes='1080i', addon=addon)
    window.doModal()
