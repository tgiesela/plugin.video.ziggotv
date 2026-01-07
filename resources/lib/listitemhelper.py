"""
Listitem helpers
"""
import os
from datetime import datetime
import time
from urllib.parse import quote, urlencode

import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon

from resources.lib import utils
from resources.lib.channel import Channel, ChannelList
from resources.lib.channelguide import ChannelGuide
from resources.lib.globals import S, G, CONST_BASE_HEADERS
from resources.lib.recording import Poster, Recording, RecordingList, SavedStateList, SingleRecording, SeasonRecording, PlannedRecording
from resources.lib.utils import ProxyHelper, SharedProperties
from resources.lib.webcalls import LoginSession

try:
    # pylint: disable=import-error, broad-exception-caught
    from inputstreamhelper import Helper # type: ignore
except Exception as excpt:
    from tests.testinputstreamhelper import Helper



class ListitemHelper:
    """
    Class holding several methods to create listitems for a specific purpose
    """

    def __init__(self, addon):
        self.ADDON: xbmcaddon.Addon = addon
        self.uuId = SharedProperties(addon=self.ADDON).get_uuid()
        self.helper = ProxyHelper(addon)
        self.customerInfo = self.helper.dynamic_call(LoginSession.get_customer_info)
        self.home = SharedProperties(addon=self.ADDON)
        self.kodiMajorVersion = self.home.get_kodi_version_major()
        self.kodiMinorVersion = self.home.get_kodi_version_minor()
        self.channelList: ChannelList = None
        self.savedStateList: SavedStateList = SavedStateList(self.ADDON)

    @staticmethod
    def __get_pricing_from_offer(instance):
        if 'offers' in instance:
            offer = instance['offers'][0]
            price = '({0} {1})'.format(offer['priceDisplay'], offer['currency'])
            return price
        return '(???)'

    def __get_widevine_license(self):
        addonPath = xbmcvfs.translatePath(self.ADDON.getAddonInfo('profile'))
        # pylint: disable=unspecified-encoding
        with open(addonPath + "widevine.json", mode="r") as certFile:
            contents = certFile.read()

        return contents

    # def __send_notification(self, item: myListItem, token, locator):
    #     tag: xbmc.InfoTagVideo = item.getVideoInfoTag()
    #     uniqueid = tag.getUniqueID('ziggochannelid')
    #     params = {'sender': self.ADDON.getAddonInfo('id'),
    #               'message': tag.getTitle(),
    #               'data': {'command': 'play_video',
    #                        'command_params': {'uniqueId': uniqueid, 'streamingToken': token, 'locator': locator}
    #                        },
    #               }

    #     command = json.dumps({'jsonrpc': '2.0',
    #                           'method': 'JSONRPC.NotifyAll',
    #                           'params': params,
    #                           'id': 1,
    #                           })
    #     xbmc.executeJSONRPC(command)

    def listitem_from_url(self, requesturl, streamingToken, drmContentId) -> xbmcgui.ListItem:
        """
        create a listitem from an url
        @param requesturl:
        @param streamingToken:
        @param drmContentId:
        @return: ListItem
        """

        isHelper = Helper(G.PROTOCOL, drm=G.DRM)
        isHelper.check_inputstream()

        li = xbmcgui.ListItem(path=requesturl)
        li.setProperty('IsPlayable', 'true')
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        tag.setMediaType('video')
        li.setMimeType('application/dash+xml')
        li.setContentLookup(False)
        if self.kodiMajorVersion >= 19:
            li.setProperty(
                key='inputstream',
                value=isHelper.inputstream_addon)
        else:
            li.setProperty(
                key='inputstreamaddon',
                value=isHelper.inputstream_addon)

        li.setProperty(
            key='inputstream.adaptive.license_flags',
            value='persistent_storage')
        # See wiki of InputStream Adaptive. Also depends on header in manifest response. See Proxyserver.
        if self.kodiMajorVersion < 21:
            li.setProperty(
                key='inputstream.adaptive.manifest_type',
                value=G.PROTOCOL)
        li.setProperty(
            key='inputstream.adaptive.license_type',
            value=G.DRM)
        licenseHeaders = dict(CONST_BASE_HEADERS)
        # 'Content-Type': 'application/octet-stream',
        licenseHeaders.update({
            'Host': G.ZIGGO_HOST,
            'x-streaming-token': streamingToken,
            'X-cus': self.customerInfo['customerId'],
            'x-go-dev': self.uuId,
            'x-drm-schemeId': 'edef8ba9-79d6-4ace-a3c8-27dcd51d21ed',
            'deviceName': 'Firefox'
        })
        extraHeaders = ProxyHelper(self.ADDON).dynamic_call(LoginSession.get_extra_headers)
        for key in extraHeaders:
            licenseHeaders.update({key: extraHeaders[key]})

        port = self.ADDON.getSetting('proxy-port')
        ip = self.ADDON.getSetting('proxy-ip')
        url = 'http://{0}:{1}/license'.format(ip, port)
        params = {'ContentId': drmContentId,
                  'addon': self.ADDON.getAddonInfo('id')}
        url = (url + '?' + urlencode(params) +
               '|' + urlencode(licenseHeaders) +
               '|R{SSM}'
               '|')
        # Prefix for request {SSM|SID|KID|PSSH}
        # R - The data will be kept as is raw
        # b - The data will be base64 encoded
        # B - The data will be base64 encoded and URL encoded
        # D - The data will be decimal converted (each char converted as integer concatenated by comma)
        # H - The data will be hexadecimal converted (each character converted as hexadecimal and concatenated)
        # Prefix for response
        # -  Not specified, or, R if the response payload is in binary raw format
        # B if the response payload is encoded as base64
        # J[license tokens] if the response payload is in JSON format. You must specify the license tokens
        #    names to allow inputstream.adaptive searches for the license key and optionally the HDCP limit.
        #    The tokens must be separated by ;. The first token must be for the key license, the second one,
        #    optional, for the HDCP limit. The HDCP limit is the result of resolution width multiplied for
        #    its height. For example to limit until to 720p: 1280x720 the result will be 921600.
        # BJ[license tokens] same meaning of J[license tokens] but the JSON is encoded as base64.
        # HB if the response payload is after two return chars \r\n\r\n in binary raw format.

        li.setProperty(
            key='inputstream.adaptive.license_key',
            value=url)
        # Test
        # server certificate to be used to encrypt messages to the license server. Should be encoded as Base64
        widevineCertificate = self.__get_widevine_license()
        li.setProperty(
            key='inputstream.adaptive.server_certificate',
            value=widevineCertificate)
        li.setProperty(
            key='inputstream.adaptive.stream_headers',
            value='x-streaming-token={0}'.format(streamingToken))
#        self.__send_notification(li, streamingToken, url)  # send the streaming-token to the Service

        return li

    def __addrecordingproperties(self, li: xbmcgui.ListItem, recording: Recording):
        li.setProperty('isrecording','true')
        li.setProperty('typeofrecording',recording.recordingState)

        startTime = utils.DatetimeHelper.from_unix(utils.DatetimeHelper.to_unix(recording.startTime, '%Y-%m-%dT%H:%M:%S.%fZ'))
        endTime = utils.DatetimeHelper.from_unix(utils.DatetimeHelper.to_unix(recording.endTime, '%Y-%m-%dT%H:%M:%S.%fZ'))
        startTime = utils.DatetimeHelper.from_utc_to_local(startTime)
        endTime = utils.DatetimeHelper.from_utc_to_local(endTime)
        li.setProperty('recEventStartDate', startTime.strftime('%Y-%m-%d'))
        li.setProperty('recEventStartTime', startTime.strftime('%H:%M'))
        li.setProperty('recEventEndTime', endTime.strftime('%H:%M'))
        li.setProperty('recEventDuration', str(endTime-startTime))
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        tag.setDuration(recording.duration)  # in seconds
        resumePoint = self.savedStateList.get(recording.id)
        if resumePoint is not None:
            li.setProperty('hasResumepoint','true')
        else:
            li.setProperty('hasResumepoint','false')

    def listitem_from_recording(self, recording: Recording, season: SeasonRecording = None) -> xbmcgui.ListItem:
        """
        Creates a ListItem from a SingleRecording
        @param season: the information of the season to which the recording belongs
        @param recording: the recording to use
        @return: listitem
        """
        try:
            start = datetime.strptime(recording.startTime,
                                      '%Y-%m-%dT%H:%M:%S.%fZ').astimezone()
        except TypeError:
            # Due to a bug in datetime see https://bugs.python.org/issue27400
            # pylint: disable=import-outside-toplevel
            import time
            start = datetime.fromtimestamp(time.mktime(time.strptime(recording.startTime,
                                                                     '%Y-%m-%dT%H:%M:%S.%fZ')))
        if recording.source == 'show':
            if recording.type == 'single':
                if hasattr(recording, 'episodeTitle'):
                    episode = f'S{recording.seasonNumber}-{recording.episodeTitle}'
                else:
                    episode = f'S{recording.seasonNumber}-E?'
            else:    
                episode = f'S{recording.seasonNumber}-E{recording.episodeNumber}'
        else:
            start = utils.DatetimeHelper.from_utc_to_local(start)
            episode = start.strftime('%Y-%m-%d %H:%M')
        title = "{0} ({1})".format(recording.title, episode)
        li = xbmcgui.ListItem(label=title)
        if recording.poster is not None:
            thumbname = xbmc.getCacheThumbName(recording.poster.url)
            thumbfile = xbmcvfs.translatePath('special://thumbnails/' + thumbname[0:1] + '/' + thumbname)
            if os.path.exists(thumbfile):
                os.remove(thumbfile)
            li.setArt({'icon': recording.poster.url,
                       'thumb': recording.poster.url,
                       'poster': recording.poster.url})
        # set the list item to playable
        li.setProperty('IsPlayable', 'true')
        li.setMimeType('application/dash+xml')
        li.setContentLookup(False)
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        if recording.isPlanned:
            tag.setTitle('[COLOR red]' + title + '[/COLOR]')
        else:
            tag.setTitle(title)
        tag.setMediaType('video')
        tag.setUniqueIDs({'ziggoRecordingId': recording.id})
        title = tag.getTitle()
        tag.setSortTitle(title)
        tag.setPlot('')
        tag.setPlotOutline('')

        self.__addrecordingproperties(li, recording)        

        # Add context menu for delete
        scriptname = self.ADDON.getAddonInfo('path') + 'contextactions.py'
        if isinstance(recording, (SingleRecording, PlannedRecording)):
            if season is not None:
                items = [(self.ADDON.getLocalizedString(S.MSG_DELETE),
                          'RunScript({0},--action=delete,--type=recording,--id={1},--rectype={2})'.format(
                              scriptname,
                              quote(recording.id),
                              recording.recordingState)),
                         (self.ADDON.getLocalizedString(S.MSG_DELETE_SEASON),
                          'RunScript({0},--action=delete,--type=season,--id={1},--rectype={2},--channel={3})'.format(
                              scriptname,
                              quote(season.showId),
                              recording.recordingState,
                              season.channelId))]
            else:
                items = [(self.ADDON.getLocalizedString(S.MSG_DELETE),
                          'RunScript({0},--action=delete,--type=recording,--id={1},--rectype={2})'.format(
                              scriptname,
                              quote(recording.id),
                              recording.recordingState))]
        else:
            items = []
        items.append((self.ADDON.getLocalizedString(S.BTN_PLAY),
                      'RunAddon({0},action=play&type=recording&id={1}&rectype={2})'.format(
                          self.ADDON.getAddonInfo('id'),
                          quote(recording.id),
                          recording.recordingState)))
        li.addContextMenuItems(items, True)

        return li

    def listitem_from_recording_season(self, recording: SeasonRecording) -> xbmcgui.ListItem:
        """
        Creates a ListItem from a SeasonRecording
        @param recording: the recording to use
        @param recType: the type of recording (planned|recorded)
        @return: listitem
        """
        description = self.ADDON.getLocalizedString(S.MSG_EPISODES).format(len(recording.episodes))
        title = "{0} ({1})".format(recording.title, description)
        li = xbmcgui.ListItem(label=title)
        thumbname = xbmc.getCacheThumbName(recording.poster.url)
        thumbfile = xbmcvfs.translatePath('special://thumbnails/' + thumbname[0:1] + '/' + thumbname)
        if os.path.exists(thumbfile):
            os.remove(thumbfile)
        li.setArt({'poster': recording.poster.url})
        # set the list item to playable
        li.setProperty('IsPlayable', 'false')
        li.setMimeType('application/dash+xml')
        li.setContentLookup(False)
        li.setIsFolder(True)
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        tag.setTitle(title)
        # tag.setSetId(recording.id)
        tag.setMediaType('video')
        tag.setUniqueIDs({'ziggoRecordingId': recording.id})
        tag.setSortTitle(title)
        tag.setPlot(recording.shortSynopsis)
        tag.setPlotOutline('')

        li.setProperty('isseasonrecording','true')

        scriptname = self.ADDON.getAddonInfo('path') + 'contextactions.py'
        if isinstance(recording, SeasonRecording):
            items = [(self.ADDON.getLocalizedString(S.MSG_DELETE),
                      'RunScript({0},--action=delete,--type=season,--id={1},--rectype={2},--channel={3})'.format(
                          scriptname,
                          quote(recording.showId),
                          recording.recordingtype,
                          recording.channelId))]
            li.addContextMenuItems(items, True)
        return li

    def findchannel(self,li: xbmcgui.ListItem, channels) -> Channel:
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        id = tag.getUniqueID('ziggochannelid')
        channel: Channel = None
        for channel in channels:
            if id == channel.id:
                return channel
        return None   

    def sort_channellistitems(self, listing: list, sortby: int, sortorder: int):
        if int(sortby) == SharedProperties.TEXTID_NAME:
            if int(sortorder) == SharedProperties.TEXTID_ASCENDING:
                listing.sort(key=lambda x: x.getLabel().lower())
            else:
                listing.sort(key=lambda x: x.getLabel().lower(), reverse=True)
        elif int(sortby) == SharedProperties.TEXTID_NUMBER:
            if int(sortorder) == SharedProperties.TEXTID_ASCENDING:
                listing.sort(key=lambda x: int(x.getVideoInfoTag().getUniqueID('ziggochannelnumber')))
            else:
                listing.sort(key=lambda x: int(x.getVideoInfoTag().getUniqueID('ziggochannelnumber')), reverse=True)

    def sort_recordinglistitems(self, listing: list, sortby: int, sortorder: int):
        if int(sortby) == SharedProperties.TEXTID_NAME:
            if int(sortorder) == SharedProperties.TEXTID_ASCENDING:
                listing.sort(key=lambda x: x.getLabel().lower())
            else:
                listing.sort(key=lambda x: x.getLabel().lower(), reverse=True)
        elif int(sortby) == SharedProperties.TEXTID_NUMBER:
            # We do not sort on number for recordings
            pass
        elif int(sortby) == SharedProperties.TEXTID_DATE:
            if int(sortorder) == SharedProperties.TEXTID_ASCENDING:
                listing.sort(key=lambda x: int(x.getVideoInfoTag().getUniqueID('ziggochannelnumber')))
            else:
                listing.sort(key=lambda x: int(x.getVideoInfoTag().getUniqueID('ziggochannelnumber')), reverse=True)

    def updateEventDetails(self, li: xbmcgui.ListItem, channels):
        channel = self.findchannel(li, channels)
        if channel is not None:
            event = self.__updateEvent(channel, li)
            if event is not None:
                if not event.hasDetails:
                    event.details = self.helper.dynamic_call(LoginSession.get_event_details, eventId=event.id)
                details = event.details
#                genres = ', '.join(details.genres)
#                li.setProperty('epgEventGenres',genres)
#                li.setProperty('epgEventDescription', details.description)
                tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
                cast = []
                for person in event.details.actors:
                    cast.append(xbmc.Actor(name=person, role=''))
                tag.setCast(cast)
                tag.setPlot(details.description)
                tag.setGenres(details.genres)
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

    def findrecording(self, li: xbmcgui.ListItem, recordings: RecordingList, recfilter):
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        id = tag.getUniqueID('ziggoRecordingId')
        recording: Recording = None
        if recfilter == str(SharedProperties.TEXTID_RECORDED):
            rectype = 'recorded'
        else:
            rectype = 'planned'

        for recording in recordings.recs:
            if id == recording.id:
                return recording
            elif isinstance(recording, SeasonRecording):
                episode: Recording
                for episode in recording.get_episodes(rectype):
                    if id == episode.id:
                        return episode
        return None   

    def updateRecordingDetails(self, li: xbmcgui.ListItem, recordings: RecordingList, recfilter):
        recording = self.findrecording(li, recordings, recfilter)
        details = None
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        if isinstance(recording, (SingleRecording, PlannedRecording)):
            details = self.helper.dynamic_call(LoginSession.get_recording_details, recordingId=recording.id)
            if details is None:
                return

            tag.setGenres(details['genres'])
            cast = []
            if 'cast' in details:
                for person in details['cast']:
                    cast.append(xbmc.Actor(name=person, role=''))
            tag.setCast(cast)
            if 'synopsis' in details:
                tag.setPlot(details['synopsis'])
            if 'shortSynopsis' in details:
                tag.setPlotOutline(details['shortSynopsis'])
            if 'episode' in details:
                tag.setEpisode(int(details['episodeNumber']))
            if 'season' in details:
                tag.setSeason(int(details['seasonNumber']))
        elif isinstance(recording, SeasonRecording):
            srec: SeasonRecording = recording
            tag.setGenres(srec.genres)
            tag.setPlot(srec.shortSynopsis)
            tag.setPlotOutline(srec.shortSynopsis)

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

    def refreshepg(self):
        """
        Refreshes the EPG data in the listitems
        """
        if self.channelList is None:
            return
        # Obtain events
        self.epg = ChannelGuide(self.ADDON, self.channelList.channels)
        self.epg.obtain_events()

    def listitem_from_channel(self, channel: Channel) -> xbmcgui.ListItem:
        """
        Creates a ListItem from a Channel
        To select only channels that are entitled use the channelList property to supply the ChannelList, 
        otherwise all channels are considered entitled.

        @param channel: the channel
        @return: listitem
        """
        if self.channelList is not None:
            subscribed = self.channelList.is_entitled(channel)
        else:
            subscribed = True

        # Obtain events
        if self.epg is None:
            self.refreshepg()

        li = xbmcgui.ListItem(label="{0}".format(channel.name))
        thumbname = xbmc.getCacheThumbName(channel.logo['focused'])
        thumbfile = xbmcvfs.translatePath('special://thumbnails/' + thumbname[0:1] + '/' + thumbname)
        if os.path.exists(thumbfile):
            os.remove(thumbfile)
        if len(channel.streamInfo.imageStream) > 0:
            thumbname = xbmc.getCacheThumbName(channel.streamInfo.imageStream['full'])
            thumbfile = (
                xbmcvfs.translatePath(
                    'special://thumbnails/' + thumbname[0:1] + '/' + thumbname.split('.', maxsplit=1)[0] + '.jpg'))
            if os.path.exists(thumbfile):
                os.remove(thumbfile)
            li.setArt({'icon': channel.logo['focused'],
                       'thumb': channel.logo['focused'],
                       'poster': channel.streamInfo.imageStream['full']})
        else:
            li.setArt({'icon': channel.logo['focused'],
                       'thumb': channel.logo['focused']})
        # set the list item to playable
        li.setProperty('IsPlayable', 'true')
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        tag.setTitle("{0}. {1}".format(channel.logicalChannelNumber, channel.name))
        tag.setGenres(channel.genre)
        tag.setSetId(channel.logicalChannelNumber)
        tag.setMediaType('video')
        tag.setUniqueIDs({'ziggochannelid': channel.id, 'ziggochannelnumber': str(channel.logicalChannelNumber)})

        title = tag.getTitle()
        tag.setSortTitle(title)
        tag.setPlot('')
        tag.setPlotOutline('')

        # if epg info available, we can add additional tags
        # epg.load_stored_events()
        channel.events = self.epg.get_events(channel.id)
        self.__updateEvent(channel, li)

            #  see https://alwinesch.github.io/group__python___info_tag_video.html#gaabca7bfa2754c91183000f0d152426dd
            #  for more tags

        li.setProperty('IsPlayable', 'true')
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
        li.setMimeType('application/dash+xml')
        li.setContentLookup(False)

        return li

    def find_entitled_offer(self, instance):
        for offer in instance['offers']:
            if offer['entitled']:
                return offer
        return None

    def __addmovieproperties(self, li: xbmcgui.ListItem, movie):
        li.setProperty('ismovie','true')

        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        resumePoint = self.savedStateList.get(movie['id'])
        if resumePoint is not None:
            li.setProperty('hasResumepoint','true')
        else:
            li.setProperty('hasResumepoint','false')
    
    def listitem_from_movie(self, item, details, instance):
        """
        Creates a ListItem from a Movie
        @param item: the movie information
        @param details: the movie details
        @param instance: list of instances that can be played
        @return: listitem
        """

        li = xbmcgui.ListItem(label=item['id'])
        if 'image' in item:
            li.setArt({'poster': item['image']})
        else:
            li.setArt({'poster': G.STATIC_URL + 'image-service/intent/{crid}/posterTile'.format(crid=item['id'])})
        # set the list item to playable
        li.setProperty('IsPlayable', 'true')
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        tag.setTitle(details['title'])
        tag.setSortTitle(details['title'])
        if 'synopsis' in details:
            tag.setPlot(details['synopsis'])
        tag.setPlotOutline('')
        if 'genres' in details:
            tag.setGenres(details['genres'])
        cast = []
        if 'castAndCrew' in details:
            cast = []
            for person in details['castAndCrew']:
                cast.append(xbmc.Actor(name=person['name'], role=person['role']))
            tag.setCast(cast)

        tag.setMediaType('video')
        li.setMimeType('application/dash+xml')
        offer = self.find_entitled_offer(instance)
        if offer is None:
            title = tag.getTitle()
            tag.setTitle('[COLOR red]' + title + self.__get_pricing_from_offer(instance) + '[/COLOR]')
            li.setProperty('IsPlayable', 'false')
        else:
            tag.setUniqueIDs({'ziggomovieid': item['id'],'ziggoinstanceid':instance['id'],'ziggoofferid': offer['id']})
        # if instance['offers'][0]['entitled']:
        #     entitled = True
        #     tag.setUniqueIDs({'ziggomovieid': instance['offers'][0]['id']})
        # else:
        #     offer = instance['offers'][0]
        #     if int(offer) == 0:
        #         entitled = True
        self.__addmovieproperties(li, item)
        li.setContentLookup(False)

        return li

    @staticmethod
    def listitem_from_movieoverview(item, overview):
        """
        Creates a ListItem from a Series/Show
        @param item: the series/show information
        @return: ListItem
        """
        li = xbmcgui.ListItem(label=item['id'])
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        if 'image' in item:
            li.setArt({'poster': item['image']})
        else:
            li.setArt({'poster': G.STATIC_URL + 'image-service/intent/{crid}/posterTile'.format(crid=item['id'])})
        # set the list item to playable
        li.setProperty('IsPlayable', 'false')
        li.setProperty('IsSeries', 'true')
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        tag.setUniqueIDs({'ziggoseriesid': item['id']})
        if 'title' in item:
            tag.setTitle(item['title'])
            tag.setSortTitle(item['title'])
        else:
            if 'gridLink' in item and 'title' in item['gridLink']:
                tag.setTitle(item['gridLink']['title'])
                tag.setSortTitle(item['gridLink']['title'])
            else:
                tag.setTitle('<>')
                tag.setSortTitle('<>')
        tag.setPlot(overview['synopsis'])
        tag.setMediaType('set')
        if 'genres' in overview:
            tag.setGenres(overview['genres'])

        li.setIsFolder(True)
        return li

    @staticmethod
    def listitem_from_genre(genre):
        """
        Creates a ListItem from a Genre
        @param genre: the genre information
        @return: ListItem
        """
        li = xbmcgui.ListItem(label=genre['id'])
        if 'image' in genre:
            li.setArt({'poster': genre['image']})
        else:
            li.setArt({'poster': G.STATIC_URL + 'image-service/intent/{crid}/posterTile'.format(crid=genre['id'])})
        # set the list item to playable
        li.setProperty('IsPlayable', 'true')
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        tag.setTitle(genre['gridLink']['title'])
        tag.setSortTitle(genre['gridLink']['title'])
        tag.setMediaType('set')
        tag.setGenres([tag.getTitle()])  # Genre is same as title here

        return li

    @staticmethod
    def listitem_from_season(season, episodes):
        """
        Creates a ListItem from a Series/Show season
        @param season: the series/show season information
        @param episodes: episode information
        @return: ListItem
        """
        li = xbmcgui.ListItem(label=season['id'])
        if 'image' in season:
            li.setArt({'poster': season['image']})
        else:
            li.setArt({'poster': G.STATIC_URL + 'image-service/intent/{crid}/posterTile'.format(crid=season['id'])})
        # set the list item to playable
        li.setProperty('IsPlayable', 'false')
        li.setProperty('IsSeason', 'true')
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        tag.setUniqueIDs({'ziggoseasonid': season['id']})
        tag.setTitle('{0}. {1}'.format(season['season'], season['title']))
        tag.setSortTitle('{0}. {1}'.format(season['season'], season['title']))
        if 'synopsis' in episodes:
            tag.setPlot(episodes['synopsis'])
        tag.setMediaType('season')
        tag.setSeason(len(episodes['seasons']))
        tag.setYear(int(episodes['startYear']))
        if 'genres' in episodes:
            tag.setGenres(episodes['genres'])

        return li

    def listitem_from_episode(self, item, season, details, instance):
        # pylint: disable=too-many-branches
        """
        Creates a ListItem from a Series/Show episode
        @param item: episode information
        @param season: the series/show season information
        @param details: details of the episode
        @param instance: list of instances that can be played
        @return: ListItem
        """
        li = xbmcgui.ListItem(label=item['id'])
        if 'image' in item:
            li.setArt({'poster': item['image']})
        else:
            li.setArt({'poster': G.STATIC_URL + 'image-service/intent/{crid}/posterTile'.format(crid=item['id'])})
        # set the list item to playable
        li.setProperty('IsPlayable', 'true')
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        if 'title' in item:
            tag.setTitle(item['title'])
            tag.setSortTitle(item['title'])
        elif 'episode' in item:
            tag.setTitle('Aflevering {0}'.format(item['episode']))
            tag.setSortTitle('Aflevering {0}'.format(item['episode']))
        if 'synopsis' in season:
            tag.setPlot(season['synopsis'])
        else:
            if 'synopsis' in item:
                tag.setPlot(item['synopsis'])
        tag.setPlotOutline('')
        entitled = False
        if 'entitlementState' in item['source']:
            if item['source']['entitlementState'] == 'entitled':
                entitled = True
        if 'genres' in details:
            tag.setGenres(details['genres'])
        if 'castAndCrew' in details:
            cast = []
            for person in details['castAndCrew']:
                cast.append(xbmc.Actor(name=person['name'], role=person['role']))
            tag.setCast(cast)

        tag.setMediaType('episode')
        li.setMimeType('application/dash+xml')
        tag.setSeason(season['season'])
        tag.setEpisode(item['episode'])

        offer = self.find_entitled_offer(instance)
        if offer is None:
            title = tag.getTitle()
            tag.setTitle('[COLOR red]' + title + self.__get_pricing_from_offer(instance) + '[/COLOR]')
            li.setProperty('IsPlayable', 'false')
        else:
            tag.setUniqueIDs({'ziggomovieid': item['id'],'ziggoinstanceid':instance['id'],'ziggoofferid': offer['id']})
        # if instance is not None:
        #     offer = self.find_entitled_offer(instance)
        #     if offer is None:
        #         title = tag.getTitle()
        #         tag.setTitle('[COLOR red]' + title + self.__get_pricing_from_offer(instance) + '[/COLOR]')
        #         li.setProperty('IsPlayable', 'false')
        #     else:
        #         tag.setUniqueIDs({'ziggomovieid': item['id'],
        #                           'ziggoinstanceid':instance['id'],
        #                           'ziggoofferid': offer['id']})
        #         entitled = True
        # else:
        #     tag.setTitle('[COLOR red]' + tag.getTitle() + '[/COLOR]')
        if not entitled:
            li.setProperty('IsPlayable', 'false')
        self.__addmovieproperties(li, item)
        li.setContentLookup(False)

        return li
