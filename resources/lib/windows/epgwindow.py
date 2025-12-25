import time
import xbmc
import xbmcgui
import xbmcaddon

from resources.lib import utils
from resources.lib.channel import Channel, ChannelList
from resources.lib.channelguide import ChannelGuide
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.utils import ProxyHelper
from resources.lib.videohelpers import VideoHelpers
from resources.lib.webcalls import LoginSession

class epgWindow(xbmcgui.WindowXML):
    CHANNELLIST = 50
    EVENTLIST = 51
    def __init__(self, xmlFilename, scriptPath, defaultSkin = "Default", defaultRes = "720p", isMedia = False, addon:xbmcaddon.Addon=None):
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes, isMedia)
        self.ADDON = addon
        self.helper = ProxyHelper(self.ADDON)
        self.listitemHelper = ListitemHelper(self.ADDON)
        self.videoHelper = VideoHelpers(self.ADDON)
        self.pos = -1
        self.show()
        self.channels: ChannelList = None
        self.channellist: xbmcgui.ControlList = None
        self.eventlist: xbmcgui.ControlList = None

    def onInit(self):
        xbmc.sleep(100)
        self.channellist = self.getControl(self.CHANNELLIST)
        self.eventlist = self.getControl(self.EVENTLIST)

    def onAction(self, action):
        super().onAction(action)

        if action.getId() == xbmcgui.ACTION_STOP:
            xbmc.log(f'Window onAction STOP', xbmc.LOGDEBUG)
            return
        
        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU or action.getId() == xbmcgui.ACTION_NAV_BACK:
            xbmc.log(f'Window onAction PREVIOUS or BACK', xbmc.LOGDEBUG)
            return
        
    def onClick(self, controlId):
        if controlId == self.CHANNELLIST:
            list: xbmcgui.ControlList = self.getControl(self.CHANNELLIST)
            li = list.getSelectedItem()
            channel = self.__findchannel(li)
            self.videoHelper.play_channel(channel=channel)
        return super().onClick(controlId)

    def showepg(self):
        list: xbmcgui.ControlList = self.getControl(self.CHANNELLIST) # Fixedlist

        # Create a list for our items.
        listing = []
        self.channels = self.helper.dynamic_call(LoginSession.get_channels)
        entitlements = self.helper.dynamic_call(LoginSession.get_entitlements)
        channels = ChannelList(self.channels, entitlements)
        channels.entitledOnly = self.ADDON.getSettingBool('allowed-channels-only')
        channels.apply_filter()

        # Obtain events
        epg = ChannelGuide(self.ADDON, self.channels)
        epg.obtain_events()

        # Iterate through channels
        channel: Channel = None
        for channel in channels:
            subscribed = channels.is_entitled(channel)
            li = self.listitemHelper.listitem_from_channel(channel)
            tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
            title = tag.getTitle()
            tag.setSortTitle(title)
            tag.setPlot('')
            tag.setPlotOutline('')

            # if epg info available, we can add additional tags
            # epg.load_stored_events()
            channel.events = epg.get_events(channel.id)

            if not subscribed:
                li.setProperty('IsPlayable', 'false')
            if channel.locators['Default'] is None:
                li.setProperty('IsPlayable', 'false')
            li.setProperty('IsPlayable', 'false')  # Turn off to avoid kodi complaining about item not playing
            listing.append(li)

        list.addItems(listing)

def loadchannelWindow(addon:xbmcaddon.Addon):
    CWD: str=addon.getAddonInfo('path')
    epgwindow = epgWindow('channels.xml', CWD, defaultRes='1080i',addon=addon)
    epgwindow.showepg()
    epgwindow.doModal()