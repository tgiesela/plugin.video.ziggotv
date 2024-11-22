"""
Module containing classes to help with creating video stream
"""
import json
from datetime import datetime, timedelta

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.avstream import StreamSession
from resources.lib.channel import Channel, ChannelList
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.recording import SingleRecording, SavedStateList
from resources.lib.streaminginfo import ReplayStreamingInfo
from resources.lib.urltools import UrlTools
from resources.lib.events import Event
from resources.lib.globals import S, G
from resources.lib.utils import ProxyHelper, SharedProperties, WebException
from resources.lib.webcalls import LoginSession
from resources.lib.ziggoplayer import ZiggoPlayer

try:
    # pylint: disable=import-error, broad-exception-caught
    from inputstreamhelper import Helper
except Exception as excpt:
    from tests.testinputstreamhelper import Helper

class VideoItem:
    """
    Class to hold information for a Video stream
    """

    # pylint: disable=too-few-public-methods
    def __init__(self, addon, streamInfo, locator=None):
        self.urlHelper = UrlTools(addon)
        self.liHelper: ListitemHelper = ListitemHelper(addon)
        self.streamInfo = streamInfo
        self.addon = addon
        if locator is None:
            if hasattr(streamInfo, 'url'):
                self.url = self.urlHelper.build_url(streamInfo.token, streamInfo.url)
            else:
                raise RuntimeError('url or locator missing')
        else:
            self.url = self.urlHelper.build_url(streamInfo.token, locator)
        self.playItem = self.liHelper.listitem_from_url(requesturl=self.url,
                                                        streamingToken=streamInfo.token,
                                                        drmContentId=streamInfo.drmContentId)

    def stop(self):
        """
        Function to stop streaming the video
        @return:
        """
        helper = ProxyHelper(self.addon)
        helper.dynamic_call(StreamSession.stop_stream, token=self.streamInfo.token)


class VideoHelpers:
    """
    class with helper functions to prepare playing a video/recording etc.
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, addon: xbmcaddon.Addon):
        self.addon = addon
        self.helper = ProxyHelper(addon)
        self.player: ZiggoPlayer = None
        self.liHelper: ListitemHelper = ListitemHelper(addon)
        self.customerInfo = self.helper.dynamic_call(LoginSession.get_customer_info)
        self.entitlements = self.helper.dynamic_call(LoginSession.get_entitlements)
        self.channels = ChannelList(self.helper.dynamic_call(LoginSession.get_channels), self.entitlements)
        self.uuId = SharedProperties(addon=self.addon).get_uuid()
        isHelper = Helper(G.PROTOCOL, drm=G.DRM)
        isHelper.check_inputstream()


    def user_wants_switch(self):
        """
        ask the use if a switch to channel is requested
        @return:
        """
        choice = xbmcgui.Dialog().yesno('Play',
                                        self.addon.getLocalizedString(S.MSG_SWITCH),
                                        self.addon.getLocalizedString(S.BTN_CANCEL),
                                        self.addon.getLocalizedString(S.BTN_SWITCH),
                                        False,
                                        xbmcgui.DLG_YESNO_NO_BTN)
        return choice

    def __add_event_info(self, playItem, channel: Channel, event):
        if event is not None:
            title = '{0}. {1}: {2}'.format(channel.logicalChannelNumber, channel.name, event.title)
            if not event.hasDetails:
                event.details = self.helper.dynamic_call(LoginSession.get_event_details, eventId=event.id)
        else:
            title = '{0}. {1}'.format(channel.logicalChannelNumber, channel.name)
        tag: xbmc.InfoTagVideo = playItem.getVideoInfoTag()
        playItem.setLabel(title)
        if event is not None:
            tag.setPlot(event.details.description)
            if event.details.isSeries:
                tag.setEpisode(event.details.episode)
                tag.setSeason(event.details.season)
            tag.setArtists(event.details.actors)
            genres = []
            for genre in event.details.genres:
                genres.append(genre)
        else:
            genres = []
        for genre in channel.genre:
            genres.append(genre)
        tag.setGenres(genres)

    @staticmethod
    def __add_vod_info(playItem, overview):
        tag: xbmc.InfoTagVideo = playItem.getVideoInfoTag()
        playItem.setLabel(overview['title'])
        tag.setPlot(overview['synopsis'])
        tag.setGenres(overview['genres'])
        if 'episode' in overview:
            tag.setEpisode(int(overview['episode']))
        if 'season' in overview:
            tag.setSeason(int(overview['season']))

    @staticmethod
    def __add_recording_info(playItem, overview):
        tag: xbmc.InfoTagVideo = playItem.getVideoInfoTag()
        playItem.setLabel(overview['title'])
        tag.setPlot(overview['synopsis'])
        tag.setGenres(overview['genres'])
        if 'episode' in overview:
            tag.setEpisode(int(overview['episodeNumber']))
        if 'season' in overview:
            tag.setSeason(int(overview['seasonNumber']))

    def __start_play(self, item: VideoItem, startposition=None):
        self.player = ZiggoPlayer()
        self.helper.dynamic_call(StreamSession.start_stream, token=item.streamInfo.token)
        if startposition is None:
            self.player.set_replay(False, 0)
        else:
            self.player.set_replay(True, startposition)
        self.player.setItem(item)
        self.player.play(item=item.url, listitem=item.playItem)
        self.__wait_for_player()

    def __play_channel(self, channel):
        def get_token(suppressHD: bool = False):
            get_token.locator, assetType = channel.get_locator(self.addon, suppressHD)
            if get_token.locator is None:
                xbmcgui.Dialog().ok('Info', self.addon.getLocalizedString(S.MSG_CANNOTWATCH))
                return None, None
            try:
                _streamInfo = self.helper.dynamic_call(LoginSession.obtain_tv_streaming_token,
                                                       channelId=channel.id, assetType=assetType)
                return get_token.locator, _streamInfo
            except WebException as exc:
                retry = self.__handleWebException(exc, suppressHD)
                if retry:
                    return get_token(True)
                return get_token.locator, None

        streamInfo = None
        try:
            locator, streamInfo = get_token()
            if streamInfo is None:
                return None
            item = VideoItem(self.addon, streamInfo, locator)
            event = channel.events.get_current_event()
            self.__add_event_info(item.playItem, channel, event)
            self.__start_play(item)
            return item.playItem
        except WebException as webExc:
            self.__handleWebException(webExc)
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            xbmc.log('Error in __play_channel: type {0}, args {1}'.format(type(exc), exc.args), xbmc.LOGERROR)
            if streamInfo is not None and streamInfo.token is not None:
                self.helper.dynamic_call(LoginSession.delete_token, streamingId=streamInfo.token)
            return None

    def __replay_event(self, event: Event, channel: Channel):
        if not event.canReplay:
            xbmcgui.Dialog().ok('Error', self.addon.getLocalizedString(S.MSG_REPLAY_NOT_AVAIALABLE))
            return
        streamInfo: ReplayStreamingInfo = None
        try:
            streamInfo = self.helper.dynamic_call(LoginSession.obtain_replay_streaming_token,
                                                  path=event.details.eventId)
            item = VideoItem(self.addon, streamInfo)
            self.__add_event_info(item.playItem, channel, event)
            resumePoint = self.get_resume_point(event.id)
            if resumePoint > 0:
                position = int(resumePoint * 1000)
            else:
                position = streamInfo.prePaddingTime
            self.__start_play(item, startposition=position)
            self.monitor_state(event.id)
        except WebException as webExc:
            self.__handleWebException(webExc)
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            xbmc.log('Error in __replay_event: type {0}, args {1}'.format(type(exc), exc.args), xbmc.LOGERROR)
            if streamInfo is not None and streamInfo.token is not None:
                self.helper.dynamic_call(LoginSession.delete_token, streamingId=streamInfo.token)

    @staticmethod
    def __get_playable_instance(overview):
        if 'instances' in overview:
            for instance in overview['instances']:
                if instance['goPlayable']:
                    return instance

            return overview['instances'][0]  # return the first one if none was goPlayable
        return None

    def __play_vod(self, overview, resumePoint) -> xbmcgui.ListItem:
        playableInstance = self.__get_playable_instance(overview)
        if playableInstance is None:
            xbmcgui.Dialog().ok('Error', self.addon.getLocalizedString(S.MSG_CANNOTWATCH))
            return None

        streamInfo = None
        try:
            streamInfo = self.helper.dynamic_call(LoginSession.obtain_vod_streaming_token,
                                                  streamId=playableInstance['id'])
            item = VideoItem(self.addon, streamInfo)
            self.__add_vod_info(item.playItem, overview)
            if resumePoint > 0:
                position = int(resumePoint * 1000)
            else:
                position = 0
            self.__start_play(item, startposition=position)
            return item.playItem
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            xbmc.log('Error in __play_vod: type {0}, args {1}'.format(type(exc), exc.args), xbmc.LOGERROR)
            if streamInfo is not None and streamInfo.token is not None:
                self.helper.dynamic_call(LoginSession.delete_token, streamingId=streamInfo.token)
            return None

    def __play_recording(self, recording: SingleRecording, resumePoint) -> xbmcgui.ListItem:
        streamInfo = None
        try:
            streamInfo = self.helper.dynamic_call(LoginSession.obtain_recording_streaming_token, streamid=recording.id)
            item = VideoItem(self.addon, streamInfo)
            details = self.helper.dynamic_call(LoginSession.get_recording_details, recordingId=recording.id)
            self.__add_recording_info(item.playItem, details)
            if resumePoint > 0:
                position = int(resumePoint * 1000)
            else:
                position = streamInfo.prePaddingTime
            self.__start_play(item, startposition=position)
            return item.playItem
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            xbmc.log('Error in __play_vod: type {0}, args {1}'.format(type(exc), exc.args), xbmc.LOGERROR)
            if streamInfo is not None and streamInfo.token is not None:
                self.helper.dynamic_call(LoginSession.delete_token, streamingId=streamInfo.token)
            return None

    def __record_event(self, event):
        self.helper.dynamic_call(LoginSession.record_event, eventId=event.id)
        xbmcgui.Dialog().notification('Info',
                                      self.addon.getLocalizedString(S.MSG_EVENT_SCHEDULED),
                                      xbmcgui.NOTIFICATION_INFO,
                                      2000)

    def __record_show(self, event, channel):
        self.helper.dynamic_call(LoginSession.record_show, eventId=event.id, channelId=channel.id)
        xbmcgui.Dialog().notification('Info',
                                      self.addon.getLocalizedString(S.MSG_SHOW_SCHEDULED),
                                      xbmcgui.NOTIFICATION_INFO,
                                      2000)

    def update_event(self, channel: Channel, event):
        """
        update the event information in the player to reflect the current event
        @param channel:
        @param event:
        @return:
        """
        if event is not None:
            title = event.title
        else:
            title = ''

        if self.player is None:
            return

        item = self.player.getPlayingItem()
        item.setLabel('{0}. {1}: {2}'.format(channel.logicalChannelNumber, channel.name, title))
        if event is not None:
            if not event.hasDetails:
                event.details = self.helper.dynamic_call(LoginSession.get_event_details, eventId=event.id)
            tag = item.getVideoInfoTag()
            tag.setPlot(event.details.description)
            tag.setTitle(event.title)
            if event.details.isSeries:
                tag.setEpisode(event.details.episode)
                tag.setSeason(event.details.season)
            tag.setArtists(event.details.actors)
        self.player.updateInfoTag(item)

    # pylint: disable=too-many-branches
    def play_epg(self, event: Event, channel: Channel):
        """
        Function to play something from the EPG. Can be an event, record event, record show, switch to channel
        @param event:
        @param channel:
        @return:
        """
        self.stop_player()

        if not self.channels.is_entitled(channel):
            xbmcgui.Dialog().ok('Info', self.addon.getLocalizedString(S.MSG_NOT_ENTITLED))
            return
        if not event.hasDetails:
            event.details = self.helper.dynamic_call(LoginSession.get_event_details, eventId=event.id)

        if not self.channels.supports_replay(channel):
            if self.user_wants_switch():
                self.__play_channel(channel)
            return

        choices = {self.addon.getLocalizedString(S.MSG_SWITCH_CHANNEL): 'switch'}
        if event.canReplay:
            choices.update({self.addon.getLocalizedString(S.MSG_REPLAY_EVENT): 'replay'})
        if event.canRecord:
            choices.update({self.addon.getLocalizedString(S.MSG_RECORD_EVENT): 'record'})
            if event.details.isSeries:
                choices.update({self.addon.getLocalizedString(S.MSG_RECORD_SHOW): 'recordshow'})
        choices.update({self.addon.getLocalizedString(S.BTN_CANCEL): 'cancel'})
        choicesList = list(choices.keys())
        selected = xbmcgui.Dialog().contextmenu(choicesList)
        action = choices[choicesList[selected]]
        if action == 'switch':
            self.__play_channel(channel)
        elif action == 'replay':
            self.__replay_event(event, channel)
        elif action == 'record':
            self.__record_event(event)
        elif action == 'recordshow':
            self.__record_show(event, channel)
        elif action == 'cancel':
            pass

    def stop_player(self):
        """
        Function to stop a playing video. Notice we use executebuiltin to avoid a timeout on stop().
        @return:
        """
        if self.player is None:
            if xbmc.Player().isPlaying():
                xbmc.log("VIDEOHELPER executebuiltin(Playercontrol(stop))", xbmc.LOGDEBUG)
                xbmc.executebuiltin('PlayerControl(stop)')
                # xbmc.sleep(2500)  # Wait is necessary because it takes some time to stop all activity
        else:
            if self.player.isPlaying():
                xbmc.log("VIDEOHELPER executebuiltin(Playercontrol(stop))", xbmc.LOGDEBUG)
                xbmc.executebuiltin('PlayerControl(stop)')
                del self.player

    def play_movie(self, movieOverview, resumePoint) -> xbmcgui.ListItem:
        """
        Play a movie
        @param resumePoint: position where to start playing
        @param movieOverview:
        @return:
        """
        self.stop_player()
        return self.__play_vod(movieOverview, resumePoint)

    def play_recording(self, recording: SingleRecording, resumePoint):
        """
        play recording
        @param recording:
        @param resumePoint: position where to start playing
        @return:
        """
        self.stop_player()
        return self.__play_recording(recording, resumePoint)

    def play_channel(self, channel: Channel) -> xbmcgui.ListItem:
        """
        Play a channel
        @param channel:
        @return:
        """
        self.stop_player()
        return self.__play_channel(channel)

    def __wait_for_player(self):
        cnt = 0
        while cnt < 10 and not self.player.isPlaying():
            cnt += 1
            xbmc.sleep(500)
        if cnt >= 10:
            xbmcgui.Dialog().ok('Error', self.addon.getLocalizedString(S.MSG_VIDEO_NOT_STARTED))

    def monitor_state(self, path):
        """
        Function to save the position of a playing recording or replay of an event. This allows restart at
        a saved position.
        @param path:
        @return:
        """
        recList = SavedStateList(self.addon)
        savedTime = None
        while xbmc.Player().isPlaying():
            savedTime = xbmc.Player().getTime()
            xbmc.sleep(500)
        recList.add(path, savedTime)
        xbmc.log('PLAYING ITEM STOPPED: {0} at {1}'.format(path, savedTime), xbmc.LOGDEBUG)

    def get_resume_point(self, path) -> float:
        """
        Function to ask for a resume point if available. Then event or recording can be started from a
        saved position
        @param path:
        @return: position as fractional seconds
        """
        recList = SavedStateList(self.addon)
        resumePoint = recList.get(path)
        if resumePoint is None:
            return 0
        t = datetime.now().replace(hour=0, minute=0, second=0) + timedelta(seconds=resumePoint)
        selected = xbmcgui.Dialog().contextmenu(
            [self.addon.getLocalizedString(S.MSG_PLAY_FROM_BEGINNING),
             self.addon.getLocalizedString(S.MSG_RESUME_FROM).format(t.strftime('%H:%M:%S'))])
        if selected == 0:
            resumePoint = 0
        return resumePoint

    def __handleWebException(self, webExc, suppressHD=False) -> bool:
        xbmc.log(webExc.response.decode('utf-8'), xbmc.LOGERROR)
        if webExc.status == 403:
            errorMsg = json.loads(webExc.response)
            if not suppressHD:
                xbmcgui.Dialog().notification('Info',
                                              self.addon.getLocalizedString(S.MSG_FALLBACK_HD),
                                              xbmcgui.NOTIFICATION_INFO,
                                              2000)
                return True
            msg = self.addon.getLocalizedString(S.MSG_CANNOTWATCH)
            if 'error' in errorMsg and 'message' in errorMsg['error']:
                msg = msg + '\n : ' + errorMsg['error']['message']
            xbmcgui.Dialog().ok('Error', msg)
        else:
            xbmcgui.Dialog().ok('Error', self.addon.getLocalizedString(S.MSG_CANNOTWATCH) +
                                '\n status: ' + webExc.status)
        return False
