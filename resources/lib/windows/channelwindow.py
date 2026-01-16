"""
Module for live tv channel window
"""
import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.channel import Channel, ChannelList, SavedChannelsList
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.utils import ProxyHelper
from resources.lib.videohelpers import VideoHelpers
from resources.lib.webcalls import LoginSession
from resources.lib.windows.basewindow import BaseWindow

class ChannelWindow(BaseWindow):
    """
    The actual channel Window for an overview of live tv channels
    """
    LISTBOX = 50
    def __init__(self, xmlFilename, scriptPath, defaultSkin = "Default",
                 defaultRes = "720p", isMedia = False, addon:xbmcaddon.Addon=None):
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes, isMedia, addon)
        self.addon = addon
        self.helper = ProxyHelper(self.addon)
        self.listitemHelper = ListitemHelper(self.addon)
        self.videoHelper = VideoHelpers(self.addon)
        self.pos = -1
        self.show()
        self.channels: ChannelList = None
        self.savedchannelslist = SavedChannelsList(self.addon)

    def onInit(self):
        xbmc.sleep(100)

    def __storeplayingchannel(self, channel:Channel):
        if channel is not None:
            self.savedchannelslist.add(channel.id, channel.name)

    def onAction(self, action: xbmcgui.Action):
        super().onAction(action)
        listbox: xbmcgui.ControlList = self.getControl(self.LISTBOX)
        # pylint: disable=no-member
        pos = listbox.getSelectedPosition()
        if pos != self.pos:
            self.listitemHelper.update_event_details(listbox.getSelectedItem())
            self.pos = pos

        if action.getId() == xbmcgui.ACTION_STOP:
            xbmc.log('Window onAction STOP', xbmc.LOGDEBUG)
            return

        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU or action.getId() == xbmcgui.ACTION_NAV_BACK:
            xbmc.log('Window onAction PREVIOUS or BACK', xbmc.LOGDEBUG)
            return

    def onClick(self, controlId):
        super().onClick(controlId)
        if controlId == self.LISTBOX:
            listbox: xbmcgui.ControlList = self.getControl(self.LISTBOX)
            # pylint: disable=no-member
            li = listbox.getSelectedItem()
            channel = self.channels.find_channel_by_listitem(li)
            if channel is not None:
                self.videoHelper.play_channel(channel=channel)
                self.__storeplayingchannel(channel)
            else:
                xbmc.log(f'Channel not found for listitem {li.getLabel()}', xbmc.LOGERROR)

    def options_selected(self):
        """
        called when options were selected in the side window
        """
        self.showchannels()

    def showchannels(self):
        """
        Method to show the channels list
        
        :param self:
        """
        listbox: xbmcgui.ControlList = self.getControl(self.LISTBOX) # type: ignore
        # pylint: disable=no-member
        # Create a list for our items.
        listbox.reset()
        listing = []
        channels = self.helper.dynamic_call(LoginSession.get_channels)
        entitlements = self.helper.dynamic_call(LoginSession.get_entitlements)
        self.channels = ChannelList(channels, entitlements)
        self.channels.entitledOnly = self.addon.getSettingBool('allowed-channels-only')
        self.channels.apply_filter()

        # Iterate through channels
        channel: Channel = None
        self.listitemHelper.channelList = self.channels
        self.listitemHelper.refreshepg()
        for channel in self.channels:
            li = self.listitemHelper.listitem_from_channel(channel)
            listing.append(li)

        # Apply sorting
        sortby, sortorder = self.sharedproperties.get_sort_options_channels()
        self.channels.sort_listitems(listing, sortby, sortorder)
        listbox.addItems(listing)
        listbox.selectItem(0)
        self.listitemHelper.update_event_details(listbox.getSelectedItem())
        self.setFocusId(self.LISTBOX)

def load_channelwindow(addon:xbmcaddon.Addon):
    """
    function to create, load and populate the channel window
    
    :param addon: Description
    :type addon: xbmcaddon.Addon
    """
    cwd: str=addon.getAddonInfo('path')
    channels = ChannelWindow('channels.xml', cwd, defaultRes='1080i',addon=addon)
    channels.showchannels()
    channels.doModal()
