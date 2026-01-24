"""
Module containing classes to help with creating video stream
"""
import json
from datetime import datetime, timedelta
from typing import Union

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib import utils
from resources.lib.avstream import StreamSession
from resources.lib.channel import Channel, ChannelList
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.recording import SingleRecording, SavedStateList
from resources.lib.streaminginfo import ReplayStreamingInfo
from resources.lib.urltools import UrlTools
from resources.lib.events import Event
from resources.lib.globals import S, G
from resources.lib.utils import ProxyHelper, SharedProperties, WebException, ZiggoKeyMap
from resources.lib.webcalls import LoginSession
from resources.lib.ziggoplayer import ZiggoPlayer
from resources.lib.movies import Movie, OfferType, Instance, Episode, Asset, SeriesList

try:
    # pylint: disable=import-error, broad-exception-caught
    from inputstreamhelper import Helper # type: ignore
except Exception as excpt:
    from tests.testinputstreamhelper import Helper

class VideoItem:
    """
    Class to hold information for a Video stream
    """

    # pylint: disable=too-few-public-methods
    def __init__(self, addon, streamInfo, locator=None) -> xbmcgui.ListItem:
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
        self.playItem:xbmcgui.ListItem = \
            self.liHelper.listitem_from_url(requesturl=self.url,
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
    Note all video play actions must be performed via this class, this includes 
    starting and stopping of playing video/live tv.
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
        self.keymap = ZiggoKeyMap(self.addon)
        isHelper = Helper(G.PROTOCOL, drm=G.DRM)
        isHelper.check_inputstream()
        # Used for updating events when playing a live channel
        self.updateeventsignal: utils.TimeSignal = None
        self.currentchannel = None

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

    def __add_asset_info(self, playItem: xbmcgui.ListItem, asset: Asset):
        tag: xbmc.InfoTagVideo = playItem.getVideoInfoTag()
        tag.setPlot(asset.synopsis)
        tag.setGenres(asset.genres)

    def __add_vod_info(self, playItem: xbmcgui.ListItem, item: Union[Movie,Episode]):
        tag: xbmc.InfoTagVideo = playItem.getVideoInfoTag()
        title = item.title
        playItem.setLabel(title)
        self.__add_asset_info(playItem, item.asset)
        if isinstance(item, Episode):
            episode: Episode = item
            tag.setEpisode(int(episode.episodenumber))
            tag.setSeason(int(episode.season.seasonnumber))

    @staticmethod
    def __add_recording_info(playItem: xbmcgui.ListItem, overview):
        tag: xbmc.InfoTagVideo = playItem.getVideoInfoTag()
        playItem.setLabel(overview['title'])
        tag.setPlot(overview['synopsis'])
        tag.setGenres(overview['genres'])
        if 'episode' in overview:
            tag.setEpisode(int(overview['episodeNumber']))
        if 'season' in overview:
            tag.setSeason(int(overview['seasonNumber']))

    def __start_play(self, item: VideoItem, startposition=None,activateKeymap: bool=False):
        self.player = ZiggoPlayer()
        self.helper.dynamic_call(StreamSession.start_stream, token=item.streamInfo.token)
        if startposition is None:
            self.player.set_replay(False, 0)
        else:
            self.player.set_replay(True, startposition)
        self.player.set_item(item)
        self.player.play(item=item.url, listitem=item.playItem)
        self.__wait_for_player()
        if activateKeymap:
            self.player.set_stop_callback(self.player_stopped)
            self.keymap.activate()
#            self.player.set_keymap(self.keymap)

    def __add_event_info(self, playItem: xbmcgui.ListItem, channel: Channel, event: Event):
        if event is not None:
            title = '{0}: {1}'.format(channel.name, event.title)
            if not event.hasDetails:
                event.details = self.helper.dynamic_call(LoginSession.get_event_details, eventId=event.id)
        else:
            title = '{0}'.format(channel.name)
        tag: xbmc.InfoTagVideo = playItem.getVideoInfoTag()

        playItem.setLabel(title)
        if event is not None:
            start = utils.DatetimeHelper.from_unix(event.startTime).strftime('%H:%M')
            end = utils.DatetimeHelper.from_unix(event.endTime).strftime('%H:%M')
            description = f'{event.details.description}\n{start}-{end}'
            tag.setPlot(description)
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
        if self.player is not None and self.player.isPlaying():
            self.player.updateInfoTag(playItem)

    def update_event(self, channel: Channel, event: Event):
        """
        update the event information in the player to reflect the current event
        @param channel:
        @param event:
        @return:
        """
        # if event is not None:
        #     title = event.title
        # else:
        #     title = ''

        # if self.player is None:
        #     return

        item: xbmcgui.ListItem = self.player.getPlayingItem()
        self.__add_event_info(item, channel, event)

    def __update_event_signal(self):
        xbmc.log('UPDATE EVENT TIMER EXPIRED', xbmc.LOGDEBUG)
        self.__stop_updateeventsignal()
        if xbmc.Player().isPlaying() and self.currentchannel is not None:
            channel: Channel = self.currentchannel
            event: Event = channel.events.get_current_event()
            if event is not None:
                now = utils.DatetimeHelper.unix_datetime(datetime.now())
                secondstogo = event.endTime - now
                endTime = utils.DatetimeHelper.from_unix(event.endTime)
                xbmc.log('EventEndTime {0}, now: {1}, secondstogo: {2}'.format(
                    endTime.strftime('%H:%M'), utils.DatetimeHelper.from_unix(now).strftime('%H:%M'),
                    secondstogo), xbmc.LOGDEBUG)
            else:
                secondstogo = 0  # check again in 5 minutes
            if secondstogo <= 0:
                secondstogo=60
            self.update_event(channel, event)
            self.updateeventsignal = utils.TimeSignal(secondstogo, self.__update_event_signal)
            self.updateeventsignal.start()
            xbmc.log(f'EVENT UPDATED AND NEW TIMER STARTED for {secondstogo}', xbmc.LOGDEBUG)

    def __play_channel(self, channel:Channel):
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
                retry = self.__handle_web_exception(exc, suppressHD)
                if retry:
                    return get_token(True)
                return get_token.locator, None

        streamInfo = None
        try:
            locator, streamInfo = get_token()
            if streamInfo is None:
                return None
            item = VideoItem(self.addon, streamInfo, locator)
            item.playItem.setProperty('ziggochannelid', channel.id)
#            event = channel.events.get_current_event()
#            self.__add_event_info(item.playItem, channel, event)
            self.__start_play(item, activateKeymap=True)
            self.currentchannel = channel
            self.updateeventsignal = utils.TimeSignal(1,self.__update_event_signal)
            self.updateeventsignal.start()
            return item.playItem
        except WebException as webExc:
            self.__handle_web_exception(webExc)
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            xbmc.log('Error in __play_channel: type {0}, args {1}'.format(str(exc), exc.args), xbmc.LOGERROR)
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
            item.playItem.setProperty('ziggoeventid', event.id)
            self.__add_event_info(item.playItem, channel, event)
            resumePoint = self.get_resume_point(event.id)
            if resumePoint > 0:
                position = int(resumePoint * 1000)
            else:
                position = streamInfo.prePaddingTime
            self.__start_play(item, startposition=position,activateKeymap=False)
            self.monitor_state(event.id)
        except WebException as webExc:
            self.__handle_web_exception(webExc)
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            xbmc.log('Error in __replay_event: type {0}, args {1}'.format(str(exc), exc.args), xbmc.LOGERROR)
            if streamInfo is not None and streamInfo.token is not None:
                self.helper.dynamic_call(LoginSession.delete_token, streamingId=streamInfo.token)

    def __play_vod(self, movie: Union[Movie,Episode], resumePoint, instance:Instance=None) -> xbmcgui.ListItem:
        '''
        Function to play a video on demand item.
        
        :param movie: The movie item as received from Ziggo webcall
        :param resumePoint: point at which the replay should start (0 if not applicable)
        :param instance: selected 'instance' from the movieOverview, should be 'goPlayable'
        :return: The listitem to be used by the videoplayer
        :rtype: ListItem
        '''
        if instance is None:
            playableInstance, _ = movie.asset.find_entitled_offer(OfferType.FREE)
        else:
            playableInstance = instance
        if playableInstance is None:
            xbmcgui.Dialog().ok('Error', self.addon.getLocalizedString(S.MSG_CANNOTWATCH))
            return None

        streamInfo = None
        try:
            streamInfo = self.helper.dynamic_call(LoginSession.obtain_vod_streaming_token,
                                                  streamId=playableInstance.id)
            item = VideoItem(self.addon, streamInfo)
            item.playItem.setProperty('ziggomovieid', movie.id)
            self.__add_vod_info(item.playItem, movie)
            if resumePoint > 0:
                position = int(resumePoint * 1000)
            else:
                position = 0
            self.__start_play(item, startposition=position,activateKeymap=False)
            return item.playItem
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            xbmc.log('Error in __play_vod: type {0}, args {1}'.format(str(exc), exc.args), xbmc.LOGERROR)
            if streamInfo is not None and streamInfo.token is not None:
                self.helper.dynamic_call(LoginSession.delete_token, streamingId=streamInfo.token)
            return None

    def __play_recording(self, recording: SingleRecording, resumePoint) -> xbmcgui.ListItem:
        streamInfo = None
        try:
            streamInfo = self.helper.dynamic_call(LoginSession.obtain_recording_streaming_token, streamid=recording.id)
            item = VideoItem(self.addon, streamInfo)
            item.playItem.setProperty('ziggorecordingid', recording.id)
            details = self.helper.dynamic_call(LoginSession.get_recording_details, recordingId=recording.id)
            self.__add_recording_info(item.playItem, details)
            if resumePoint > 0:
                position = int(resumePoint * 1000)
            else:
                position = streamInfo.prePaddingTime
            self.__start_play(item, startposition=position, activateKeymap=False)
            return item.playItem
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            xbmc.log('Error in __play_recording: type {0}, args {1}'.format(str(exc), exc.args), xbmc.LOGERROR)
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
#                del self.player
        while xbmc.Player().isPlaying():
            xbmc.sleep(500)
        self.player_stopped()
        # if self.updateeventsignal is not None:
        #     self.updateeventsignal.stop()
        #     self.updateeventsignal.join()
        # self.updateeventsignal = None
        # self.currentchannel = None

    def player_stopped(self):
        """
        Callback function that is called when playback stops
        """
        xbmc.log("VIDEOHELPER player_stopped callback called", xbmc.LOGDEBUG)
        self.__stop_updateeventsignal()
        self.currentchannel = None
        if self.keymap is not None:
            self.keymap.deactivate()

    def play_movie(self, movie: Union[Movie,Episode], resumePoint) -> xbmcgui.ListItem:
        """
        Play a movie
        @param resumePoint: position where to start playing
        @param movie: Movie object containing all info for playing the movie
        @return:
        """
        self.stop_player()
        if isinstance(movie, Episode) and movie.isEvent():
            episode: Episode = movie
            serieslist:SeriesList = episode.season.series.serieslist
            event: Event = serieslist.get_event(episode)
            channel = self.channels.find_channel_by_id(episode.source.channel['channelId'])
            return self.__replay_event(event, channel)
        else:
            return self.__play_vod(movie, resumePoint)

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

    def __handle_web_exception(self, webExc, suppressHD=False) -> bool:
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

    def __stop_updateeventsignal(self):
        if self.updateeventsignal is not None:
            xbmc.log('UPDATE EVENT TIMER STOPPED', xbmc.LOGDEBUG)
            self.updateeventsignal.stop()
            try:
                self.updateeventsignal.join()
            except RuntimeError:
                xbmc.log('Failed to join thread of current timer', xbmc.LOGERROR)
        self.updateeventsignal = None

    def __del__(self):
        self.__stop_updateeventsignal()
