"""
Classes for processing channels
"""
import os
import dataclasses
from typing import List, Tuple
from collections import UserList
import json
import datetime
import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
from resources.lib import utils
from resources.lib.events import EventList
from resources.lib.globals import G

class Channel:
    """
    Class to handle all channel data. More robust than querying the json string everywhere
    """
    @dataclasses.dataclass
    class ReplayInfo:
        """
        Dataclass for replay info belonging to a channel
        """
        def __init__(self, eventJson):
            self.replayPrePadding = 0
            self.replayPostPadding = 0
            self.replaySources = {}
            self.replayProducts = {}
            self.ndvrRetentionLimit = 0
            self.avadEnabled = False
            self.adSupport = []
            if 'replayPrePadding' in eventJson:
                self.replayPrePadding = eventJson['replayPrePadding']
            if 'replayPostPadding' in eventJson:
                self.replayPostPadding = eventJson['replayPostPadding']
            if 'replaySources' in eventJson:
                self.replaySources = eventJson['replaySources']
            if 'replayProducts' in eventJson:
                self.replayProducts = eventJson['replayProducts']
            if 'ndvrRetentionLimit' in eventJson:
                self.ndvrRetentionLimit = eventJson['ndvrRetentionLimit']
            if 'avadEnabled' in eventJson:
                self.avadEnabled = True
            if 'adSupport' in eventJson:
                self.adSupport = eventJson['adSupport']

    @dataclasses.dataclass
    class StreamInfo:
        """
        streaming information belonging to a channel
        """
        def __init__(self, eventJson):
            self.streamingApplications = {}
            self.externalStreamingProtocols = {}
            for streamapp in eventJson['streamingApplications']:
                self.streamingApplications[streamapp] = eventJson['streamingApplications'][streamapp]
            if 'externalStreamingProtocols' in eventJson:
                for extstreamapp in eventJson['externalStreamingProtocols']:
                    self.externalStreamingProtocols[extstreamapp] = eventJson['externalStreamingProtocols'][
                        extstreamapp]
            self.imageStream = eventJson['imageStream']

    def __init__(self, channelJson):
        # from resources.lib.events import EventList
        self.jsonData = channelJson
        self.events: EventList = EventList()
        self.logo = {}
        if 'logo' in channelJson:
            for logotype in channelJson['logo']:
                self.logo[logotype] = channelJson['logo'][logotype]
        self.locators = {}
        if 'locators' in channelJson:
            for locator in channelJson['locators']:
                self.locators[locator] = channelJson['locators'][locator]
        self.locators['Default'] = channelJson['locator']
        self.replayInfo = self.ReplayInfo(channelJson)
        if 'genre' in channelJson:
            self.genre = channelJson['genre']
        else:
            self.genre = []
        self.streamInfo = Channel.StreamInfo(channelJson)

    # properties
    # pylint: disable=missing-function-docstring
    @property
    def id(self):
        return self.jsonData['id']

    @property
    def name(self):
        return self.jsonData['name']

    @property
    def logicalChannelNumber(self):
        return self.jsonData['logicalChannelNumber']

    @property
    def resolution(self):
        return self.jsonData['resolution']

    @property
    def isHidden(self):
        if 'isHidden' in self.jsonData:
            return self.jsonData['isHidden']
        return False

    @property
    def linearProducts(self):
        return self.jsonData['linearProducts']
    # pylint: enable=missing-function-docstring

    def get_locator(self, addon: xbmcaddon.Addon, disableFullHD: bool = False) -> Tuple[str, str]:
        """
        Function to get the correct locator(url) to play a channel. The selected locator
        depends on the maximal resolution allowed according to inputstream adaptive (ISA) and
        the available type of locators.

        @param disableFullHD: option to suppress fullHD if server does not allow this
        @param addon:
        @return: URL of the channel
        """
        try:
            maxResDrm = xbmcaddon.Addon('inputstream.adaptive').getSetting('adaptivestream.res.secure.max')
            hdAllowed = maxResDrm in ['auto', '1080p', '2K', '4K', '1440p']
        # pylint: disable=broad-exception-caught
        except Exception:
            hdAllowed = True
        assetType = 'Orion-DASH'
        fullHD = addon.getSettingBool('full-hd')
        if hdAllowed and not fullHD or disableFullHD:
            hdAllowed = False
        if 'Orion-DASH-HEVC' in self.locators and hdAllowed:
            avc = self.locators['Orion-DASH-HEVC']
            assetType = 'Orion-DASH-HEVC'
        elif 'Orion-DASH' in self.locators:
            avc = self.locators['Orion-DASH']
        else:
            avc = self.locators['Default']
        return avc, assetType


class ChannelList(UserList):
    """
    class to get a list of channels with options to suppress hidden channels or only get channels
    for which you ar entitled.
    """
    def __init__(self, channels: List[Channel], entitlements):
        super().__init__(channels)
        self.channels: List[Channel] = channels
        self.__channelnumbers: List[int] = self.__create_list()
        self.filteredChannels: List[Channel] = []
        self.entitlements = entitlements
        self.suppressHidden = True
        self._entitledOnly = False
        self.entitlementList = []
        i = 0
        while i < len(entitlements['entitlements']):
            self.entitlementList.append(entitlements['entitlements'][i]["id"])
            i += 1
        self.apply_filter()

    def __create_list(self):
        channelnumbers:List[int] = []
        for channel in self.channels:
            channelnumbers.append(channel.logicalChannelNumber)
        return sorted(channelnumbers, key=int, reverse=False)

    # properties
    # pylint: disable=missing-function-docstring
    @property
    def hiddenSuppressed(self):
        return self.suppressHidden

    @hiddenSuppressed.setter
    def hiddenSuppressed(self, value):
        self.suppressHidden = value

    @property
    def entitledOnly(self):
        return self._entitledOnly

    @entitledOnly.setter
    def entitledOnly(self, value):
        self._entitledOnly = value
    # pylint: enable=missing-function-docstring

    def apply_filter(self):
        """
        Function to create the resulting list of channels based on the selected filter options:
            hiddenSuppressed
            entitledOnly
        @return:
        """
        self.filteredChannels = []
        for channel in self.channels:
            if channel.isHidden and self.suppressHidden:
                continue
            if self.entitledOnly:
                if self.is_entitled(channel):
                    self.filteredChannels.append(channel)
            else:
                self.filteredChannels.append(channel)
        self.data = self.filteredChannels

    def is_playable(self, channel: Channel):
        """
        Function to verify that the channel can be played
        
        :param self: 
        :param channel: the channel
        :type channel: Channel
        """
        if self.is_entitled(channel):
            if channel.locators['Default'] is None:
                return False
            return True
        return False

    def is_entitled(self, channel: Channel):
        """
        Checks if user is allowed to watch the channel
        @param channel:
        @return:
        """
        for product in channel.linearProducts:
            if product in self.entitlementList:
                return True
        return False

    def supports_replay(self, channel: Channel):
        """
        Checks if the channel supports replay
        @param channel:
        @return:
        """
        for product in channel.replayInfo.replayProducts:
            if product['entitlementId'] in self.entitlementList:
                if product['allowStartOver']:
                    return True
        return False

    def supports_record(self):
        """
        Checks if the channel supports recording
        @param:
        @return:
        """
        return 'PVR' in self.entitlements

    def channels_by_lcn(self, reverse=False) -> List[Channel]:
        """
        Get a list of channels sorted by logical channel number
        @return: List[Channel]
        """
        self.channels.sort(key=lambda x: x.logicalChannelNumber, reverse=reverse)
        return self.channels

    def channels_by_name(self, reverse=False) -> List[Channel]:
        """
        Get a list of channels sorted by name
        @return: List[Channel]
        """
        self.channels.sort(key=lambda x: x.name, reverse=reverse)
        return self.channels

    def sort_listitems(self, listing: list, sortby: int, sortorder: int):
        """
        Function to sort the channels in a list of listitems
        
        :param self: 
        :param listing: the list of xbmcgui.ListItems
        :type listing: list
        :param sortby: the key to sort on
        :type sortby: int
        :param sortorder: the sort order
        :type sortorder: int
        """
        if int(sortby) == utils.SharedProperties.TEXTID_NAME:
            if int(sortorder) == utils.SharedProperties.TEXTID_ASCENDING:
                listing.sort(key=lambda x: x.getLabel().lower())
            else:
                listing.sort(key=lambda x: x.getLabel().lower(), reverse=True)
        elif int(sortby) == utils.SharedProperties.TEXTID_NUMBER:
            if int(sortorder) == utils.SharedProperties.TEXTID_ASCENDING:
                listing.sort(key=lambda x: int(x.getVideoInfoTag().getUniqueID('ziggochannelnumber')))
            else:
                listing.sort(key=lambda x: int(x.getVideoInfoTag().getUniqueID('ziggochannelnumber')), reverse=True)

    def find_channel_by_id(self,channelid):
        """
        Function to find a channel by its id
        
        :param self: Description
        :param channelid: Description
        """
        channel: Channel = None
        for channel in self.channels:
            if channelid == channel.id:
                return channel
        return None

    def find_channel_by_number(self,number:int):
        """
        Function to find a channel by its number
        
        :param self: 
        :param number: the logical channel number
        :type number: int
        """
        channel: Channel = None
        for channel in self.channels:
            if number == channel.logicalChannelNumber:
                return channel
        return None

    def find_channel_by_listitem(self,li: xbmcgui.ListItem) -> Channel:
        """
        Function to find a channel based on information in the listitem
        
        :param self: 
        :param li: the listitem from which the channel info must be taken
        :type li: xbmcgui.ListItem
        :return: the found channel or None
        :rtype: Channel
        """
        channelid = li.getProperty('ziggochannelid')
        if channelid is None or channelid == '':
            tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
            channelid = tag.getUniqueID('ziggochannelid')
            if channelid is None or channelid == '':
                return None
        channel: Channel = self.find_channel_by_id(channelid)
        return channel

    def get_next_channel(self, channel: Channel) -> Channel:
        """
        Function to find the next playable channel from the list
        
        :param self: 
        :param channel: the current channel
        :type channel: Channel
        :return: the next channel
        :rtype: Channel
        """
        try:
            index = self.__channelnumbers.index(channel.logicalChannelNumber)
            if index >= 0:
                if index >= len(self.__channelnumbers):
                    newchannelnr = self.__channelnumbers[0]
                else:
                    newchannelnr = self.__channelnumbers[index+1]
                return self.find_channel_by_number(newchannelnr)
            return channel
        except ValueError:
            return channel

    def get_prev_channel(self, channel: Channel) -> Channel:
        """
        Function to find the previous playable channel from the list
        
        :param self: 
        :param channel: the current channel
        :type channel: Channel
        :return: the previous channel
        :rtype: Channel
        """
        try:
            index = self.__channelnumbers.index(channel.logicalChannelNumber)
            if index >= 0:
                if index <= 0:
                    newchannelnr = self.__channelnumbers[len(self.__channelnumbers)-1]
                else:
                    newchannelnr = self.__channelnumbers[index-1]
                return self.find_channel_by_number(newchannelnr)
            return channel
        except ValueError:
            return channel

class SavedChannelsList:
    """
    class to keep the state of played channels. This is used to present a list of recently played channels
    in the home screen.
    """

    def __init__(self, addon: xbmcaddon.Addon):
        self.addon = addon
        self.addonPath = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        self.states = {}
        self.fileName = self.addonPath + G.RECENTCHANNELS_INFO
        targetdir = os.path.dirname(self.fileName)
        if targetdir == '':
            targetdir = os.getcwd()
        if not os.path.exists(targetdir):
            os.makedirs(targetdir)
        if not os.path.exists(self.fileName):
            with open(self.fileName, 'w', encoding='utf-8') as file:
                json.dump(self.states, file)
        self.__load()

    def __load(self):
        with open(self.fileName, 'r+', encoding='utf-8') as file:
            self.states = json.load(file)

    def add(self, itemId, name):
        """
        function to add/update the position of a channel
        @param itemId:
        @param position:
        @return:
        """
        self.states.update({itemId: {'datePlayed': utils.DatetimeHelper.unix_datetime(datetime.datetime.now()),
                                     'name': name}})
        with open(self.fileName, 'w', encoding='utf-8') as file:
            json.dump(self.states, file)

    def delete(self, itemId):
        """
        function to delete the channel from the state list
        @param itemId:
        @return:
        """
        if itemId in self.states:
            self.states.pop(itemId)

    def get(self, itemId):
        """
       function to find a channel by its id
       @param itemId:
       @return:
        """
        for item in self.states:
            if item == itemId:
                return self.states[item]['datePlayed']
        return None

    def cleanup(self, daysToKeep=365, itemsToKeep=0):
        """
        function to clean up saved channels
        @param daysToKeep: 
        @return: 
        """
        expDate = datetime.datetime.now() - datetime.timedelta(days=daysToKeep)
        sortedStates = dict(sorted(self.states.items(), key=lambda x: x[1]['datePlayed'], reverse=True))
        itemsKept = 0
        for item in list(sortedStates):
            if sortedStates[item]['datePlayed'] < utils.DatetimeHelper.unix_datetime(expDate):
                if itemsKept < itemsToKeep:
                    itemsKept += 1
                else:
                    self.delete(item)
        with open(self.fileName, 'w', encoding='utf-8') as file:
            json.dump(self.states, file)

    def get_all(self):
        """
        function to get all saved channels, ordered by date played
        @return:
        """
        sortedStates = dict(sorted(self.states.items(), key=lambda x: x[1]['datePlayed'], reverse=True))
        return sortedStates
