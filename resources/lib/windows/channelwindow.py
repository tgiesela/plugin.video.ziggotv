import time
import xbmc
import xbmcgui
import xbmcaddon

from resources.lib import utils
from resources.lib.channel import Channel, ChannelList
from resources.lib.channelguide import ChannelGuide
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.utils import ProxyHelper, SharedProperties
from resources.lib.videohelpers import VideoHelpers
from resources.lib.webcalls import LoginSession
from resources.lib.windows.basewindow import baseWindow
from resources.lib.windows.sidewindow import sideWindow

class channelWindow(baseWindow):
    LISTBOX =50
    def __init__(self, xmlFilename, scriptPath, defaultSkin = "Default", defaultRes = "720p", isMedia = False, addon:xbmcaddon.Addon=None):
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes, isMedia, addon)
        self.ADDON = addon
        self.helper = ProxyHelper(self.ADDON)
        self.listitemHelper = ListitemHelper(self.ADDON)
        self.videoHelper = VideoHelpers(self.ADDON)
        self.pos = -1
        self.show()
        self.channels: ChannelList = None

    def onInit(self):
        xbmc.sleep(100)

    def __findchannel(self,li: xbmcgui.ListItem):
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        id = tag.getUniqueID('ziggochannelid')
        channel: Channel = None
        for channel in self.channels:
            if id == channel.id:
                return channel
        return None   
    
    def __updateEventDetails(self, li: xbmcgui.ListItem):
        channel = self.__findchannel(li)
        if channel is not None:
            event = self.__updateEvent(channel, li)
            if event is not None:
                if not event.hasDetails:
                    event.details = self.helper.dynamic_call(LoginSession.get_event_details, eventId=event.id)
                details = event.details
                genres = ', '.join(details.genres)
                li.setProperty('epgEventGenres',genres)
                li.setProperty('epgEventDescription', details.description)
                nextevent = channel.events.get_next_event(event)
                if nextevent is None:
                    return
                li.setProperty('epgNextEventTitle', nextevent.title)
                startTime = utils.DatetimeHelper.from_unix(nextevent.startTime)
                endTime = utils.DatetimeHelper.from_unix(nextevent.endTime)
                li.setProperty('epgNextEventStartTime', startTime.strftime('%H:%M'))
                li.setProperty('epgNextEventEndTime', endTime.strftime('%H:%M'))
                duration = time.strftime("%H:%M", time.gmtime(nextevent.duration))
                li.setProperty('epgNextEventDuration', duration)

    def __updateEvent(self, channel: Channel, li: xbmcgui.ListItem):
        event = channel.events.get_current_event()
        if event is not None:
            li.setProperty('hasepg','true')
            startTime = utils.DatetimeHelper.from_unix(event.startTime)
            endTime = utils.DatetimeHelper.from_unix(event.endTime)
            li.setProperty('epgEventStartTime', startTime.strftime('%H:%M'))
            li.setProperty('epgEventEndTime', endTime.strftime('%H:%M'))
            duration = time.strftime("%H:%M", time.gmtime(event.duration))
            li.setProperty('epgEventDuration', duration)
            tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
            tag.setDuration(event.duration)  # in seconds
            li.setProperty('epgEventTitle', event.title)
            elapsed = utils.DatetimeHelper.unix_datetime(utils.DatetimeHelper.now()) - event.startTime
            percentage = (elapsed/event.duration) * 100
            li.setProperty('epgElapsed', str(percentage))
        else:
            li.setProperty('hasepg','false')
        return event

    def onAction(self, action):
        super().onAction(action)
        list: xbmcgui.ControlList = self.getControl(self.LISTBOX)
        pos = list.getSelectedPosition()
        if pos != self.pos:
            self.__updateEventDetails(list.getSelectedItem())
            self.pos = pos

        if action.getId() == xbmcgui.ACTION_STOP:
            xbmc.log(f'Window onAction STOP', xbmc.LOGDEBUG)
            return
        
        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU or action.getId() == xbmcgui.ACTION_NAV_BACK:
            xbmc.log(f'Window onAction PREVIOUS or BACK', xbmc.LOGDEBUG)
            return
        
    def onClick(self, controlId):
        super().onClick(controlId)
        if controlId == self.LISTBOX:
            list: xbmcgui.ControlList = self.getControl(self.LISTBOX)
            li = list.getSelectedItem()
            channel = self.__findchannel(li)
            self.videoHelper.play_channel(channel=channel)

    def optionsSelected(self):
        """
        called when options were selected in the side window
        """
        self.showchannels()

    def showchannels(self):
        list: xbmcgui.ControlList = self.getControl(self.LISTBOX) # Fixedlist

        # Create a list for our items.
        list.reset()
        listing = []
        self.channels = self.helper.dynamic_call(LoginSession.get_channels)
        entitlements = self.helper.dynamic_call(LoginSession.get_entitlements)
        channelList = ChannelList(self.channels, entitlements)
        channelList.entitledOnly = self.ADDON.getSettingBool('allowed-channels-only')
        channelList.apply_filter()

        # Obtain events
        epg = ChannelGuide(self.ADDON, self.channels)
        epg.obtain_events()

        # Iterate through channels
        channel: Channel = None
        for channel in channelList:  # create a list item using the song filename for the label
            subscribed = channelList.is_entitled(channel)
            li = self.listitemHelper.listitem_from_channel(channel)
            tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
            title = tag.getTitle()
            tag.setSortTitle(title)
            tag.setPlot('')
            tag.setPlotOutline('')

            # if epg info available, we can add additional tags
            # epg.load_stored_events()
            channel.events = epg.get_events(channel.id)
            self.__updateEvent(channel, li)

            #  see https://alwinesch.github.io/group__python___info_tag_video.html#gaabca7bfa2754c91183000f0d152426dd
            #  for more tags

            if not subscribed:
                li.setProperty('IsPlayable', 'false')
            if channel.locators['Default'] is None:
                li.setProperty('IsPlayable', 'false')
            # if li.getProperty('IsPlayable') == 'true':
            #     callbackUrl = '{0}?action=play&type=channel&id={1}'.format(self.url, channel.id)
            # else:
            #     tag.setTitle(title[0:title.find('.') + 1] + '[COLOR red]' + title[title.find('.') + 1:] + '[/COLOR]')
            #     callbackUrl = '{0}?action=cantplay&video={1}'.format(self.url, channel.id)
            li.setProperty('IsPlayable', 'false')  # Turn off to avoid kodi complaining about item not playing
            listing.append(li)
        if int(self.sortby) == SharedProperties.TEXTID_NAME:
            if int(self.sortorder) == SharedProperties.TEXTID_ASCENDING:
                listing.sort(key=lambda x: x.getLabel().lower())
            else:
                listing.sort(key=lambda x: x.getLabel().lower(), reverse=True)
        elif int(self.sortby) == SharedProperties.TEXTID_NUMBER:
            if int(self.sortorder) == SharedProperties.TEXTID_ASCENDING:
                listing.sort(key=lambda x: int(x.getVideoInfoTag().getUniqueID('ziggochannelnumber')))
            else:
                listing.sort(key=lambda x: int(x.getVideoInfoTag().getUniqueID('ziggochannelnumber')), reverse=True)
        list.addItems(listing)
        list.selectItem(0)
        self.setFocusId(self.LISTBOX)

def loadchannelWindow(addon:xbmcaddon.Addon):
    CWD: str=addon.getAddonInfo('path')
    channels = channelWindow('channels.xml', CWD, defaultRes='1080i',addon=addon)
    channels.showchannels()
    channels.doModal()
