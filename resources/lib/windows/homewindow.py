"""
Module for creating and loading homewindow (initial form)
"""
import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.channel import Channel, ChannelList, SavedChannelsList
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.utils import KeyMapMonitor, ProxyHelper, check_service
from resources.lib.webcalls import LoginSession
from resources.lib.windows.basewindow import BaseWindow
from resources.lib.windows.channelwindow import load_channelwindow
from resources.lib.windows.epgwindow import load_epgwindow
from resources.lib.windows.moviewindow import load_moviewindow
from resources.lib.windows.recwindow import load_recordingwindow
class HomeWindow(BaseWindow):
    """
    Window class for the home window, which is shown when the addon is started
    """
    GROUPLIST=50
    CHANNELBUTTON=5
    EPGBUTTON=6
    RECORDINGSBUTTON=7
    MOVIESBUTTON=8
    RECENTCHANNELLIST=150
    RECENTRECORDINGSLIST=250
    def __init__(self, xmlFilename, scriptPath, defaultSkin = "Default", defaultRes = "720p",
                 isMedia = False, addon=''):
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes, isMedia, addon)
        self.addon = addon
        self.savedchannelslist = None
        self.recentchannels = None
        self.helper:ProxyHelper = ProxyHelper(self.addon)
        self.channels = self.helper.dynamic_call(LoginSession.get_channels)
        self.entitlements = self.helper.dynamic_call(LoginSession.get_entitlements)
        self.channellist:ChannelList = ChannelList(self.channels,self.entitlements)
        self.listitemHelper:ListitemHelper = ListitemHelper(self.addon)
        self.keyboardmonitor:KeyMapMonitor = KeyMapMonitor(self.addon, self.switch_tochannel)

    def __del__(self):
        self.keyboardmonitor.waitForAbort(1)
        self.keyboardmonitor = None
        xbmc.log('HOMEWINDOW Destroyed', xbmc.LOGDEBUG)
        super().__del__()

    def __get_current_channel(self):
        item: xbmcgui.ListItem = xbmc.Player().getPlayingItem()
        channel = self.channellist.find_channel_by_listitem(item)
        return channel

    def __do_play_channel(self, channel: Channel):
        self.videoHelper.play_channel(channel=channel)
        if channel is not None:
            self.savedchannelslist.add(channel.id, channel.name)

    def __showrecentchannels(self):
        self.savedchannelslist = SavedChannelsList(self.addon)
        self.recentchannels = self.savedchannelslist.get_all()
        listing = []
        # this puts the focus on the first button of the screen
        recentchannellist: xbmcgui.ControlList = self.getControl(self.RECENTCHANNELLIST)
        # pylint: disable=no-member
        self.channellist.entitledOnly = self.addon.getSettingBool('allowed-channels-only')
        self.channellist.apply_filter()
        # Obtain events

        self.listitemHelper.channelList = self.channellist
        self.listitemHelper.refreshepg()

        recentchannellist.reset()

        for recentchannel in self.recentchannels:
#            channelname = self.recentchannels[recentchannel]['name']
            channelobj:Channel = self.channellist.find_channel_by_id(recentchannel)
            if channelobj is None:
                continue
            li = self.listitemHelper.listitem_from_channel(channelobj)
#            li.setProperty('IsPlayable', 'false')  # Turn off to avoid kodi complaining about item not playing
            listing.append(li)

        recentchannellist.addItems(listing)
        recentchannellist.selectItem(0)
        self.setFocusId(5)

    def switch_tochannel(self, keysentered: str):
        """
        Function to switch to a different channel. Invoked by entering digits or page-up/down
        
        :param self: 
        :param keysentered: the keys entered (either a sequence of numeric digits or 'pageup'|'pagedown')
        :type keysentered: str
        """
        if keysentered.isnumeric():
            channel = self.channellist.find_channel_by_number(int(keysentered))
            if channel is None:
                xbmc.executebuiltin(f'Notification(Channel,{keysentered} not found)')
                return
            self.__do_play_channel(channel)
        else:
            channel = self.__get_current_channel()
            startchannel = channel.id
            if keysentered == 'pageup':
                # Find the next playable channel
                nextchannel = self.channellist.get_next_channel(channel)
                while not self.channellist.is_playable(nextchannel) and nextchannel.id != startchannel:
                    nextchannel = self.channellist.get_next_channel(nextchannel)
                if nextchannel.id != startchannel and nextchannel is not None:
                    self.__do_play_channel(nextchannel)
            elif keysentered == 'pagedown':
                prevchannel = self.channellist.get_prev_channel(channel)
                while not self.channellist.is_playable(prevchannel) and prevchannel.id != startchannel:
                    prevchannel = self.channellist.get_prev_channel(prevchannel)
                if prevchannel.id != startchannel and prevchannel is not None:
                    self.__do_play_channel(prevchannel)
            else:
                xbmc.log('Unkown command in switchToChannel', xbmc.LOGERROR)

    def onInit(self):
        # give kodi a bit of (processing) time to add all items to the container
        xbmc.sleep(100)
        self.__showrecentchannels()
        # self.__showrecentrecordings()

    # pylint: disable=useless-parent-delegation
    def onFocus(self, controlId):
        super().onFocus(controlId)

    def onAction(self, action:xbmcgui.Action):
        super().onAction(action)
        if action.getId() == xbmcgui.ACTION_STOP:
            xbmc.log('Window onAction STOP', xbmc.LOGDEBUG)
            self.close()
            return

        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU or action.getId() == xbmcgui.ACTION_NAV_BACK:
            xbmc.log('Window onAction PREVIOUS or BACK', xbmc.LOGDEBUG)
            self.close()
            return

    def onClick(self, controlId):
        super().onClick(controlId)
        if controlId == self.CHANNELBUTTON:
            load_channelwindow(self.addon)
        elif controlId == self.EPGBUTTON:
            load_epgwindow(self.addon)
        elif controlId == self.RECORDINGSBUTTON:
            load_recordingwindow(self.addon)
        elif controlId == self.MOVIESBUTTON:
            load_moviewindow(self.addon)
        elif controlId == self.RECENTCHANNELLIST:
            listctrl: xbmcgui.ControlList = self.getControl(self.RECENTCHANNELLIST)
            # pylint: disable=no-member
            li = listctrl.getSelectedItem()
            tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
            channelid = tag.getUniqueID('ziggochannelid')
            channel = self.channellist.find_channel_by_id(channelid)
            if channel is not None:
                self.__do_play_channel(channel=channel)
            else:
                xbmc.log(f'Channel not found for listitem {li.getLabel()}', xbmc.LOGERROR)

def load_homewindow(addon: xbmcaddon.Addon):
    """
    Function to create, populate and display the home window
    
    :param addon: the addon for which the form is created
    :type addon: xbmcaddon.Addon
    """
    # pylint: disable=import-outside-toplevel
    from resources.lib.utils import invoke_debugger
    invoke_debugger(False, 'vscode')
    check_service(addon)
    window = HomeWindow('ziggohome.xml', addon.getAddonInfo('path'), defaultRes='1080i', addon=addon)
    window.doModal()
    # Following is needed to stop any pending thrreads from the videoHelper which might prevent stopping Kodi
    # after the window is closed
    window.videoHelper.requestorCallbackStop = None
    window.videoHelper.player_stopped()
