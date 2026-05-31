# pylint: disable=missing-function-docstring, missing-class-docstring, missing-module-docstring
import datetime

import pytest

from resources.lib.avstream import AVStreamType, AvStream, StreamSession
from resources.lib.channel import Channel, ChannelList
from resources.lib.channelguide import ChannelGuide
from resources.lib.movies import Movie, MovieList, OfferType
from resources.lib.recording import Recording, RecordingList, RecordingType, SeasonRecording
from resources.lib.utils import WebException

class TestAvStream:
    def test_channel_get_token(self, activewebsession):
        # activewebsession.do_login()
        # activewebsession.logon_via_proxy()

        activewebsession.session.refresh_channels()
        channels = activewebsession.session.get_channels()
        entitlements = activewebsession.session.get_entitlements()
        cl = ChannelList(channels, entitlements)
        zender:Channel = cl.find_channel_by_number(1)

        result:AvStream = activewebsession.helper.dynamic_call(StreamSession.define_stream,
                                                   streamItem=zender,
                                                   suppressHD=False)
        assert result is not None
        assert result.streamInfo is not None
        assert result.streamInfo.token is not None
        
        activewebsession.helper.dynamic_call(StreamSession.start_stream,streamid=result.id)
        activewebsession.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)

        result:AvStream = activewebsession.helper.dynamic_call(StreamSession.define_stream,
                                                   streamItem=zender,
                                                   suppressHD=True)
        assert result is not None
        assert result.streamInfo is not None
        assert result.streamInfo.token is not None
        activewebsession.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)

        with pytest.raises((ValueError, WebException)):
            result:AvStream = activewebsession.helper.dynamic_call(StreamSession.define_stream,
                                                        streamItem='NOT_A_CHANNEL',
                                                        suppressHD=True)

        activewebsession.session.entitlements = {}
        result:AvStream = activewebsession.helper.dynamic_call(StreamSession.define_stream_for,
                                                   streamType=AVStreamType.CHANNEL,
                                                   streamId=zender.id,
                                                   suppressHD=False)
        assert result is not None
        assert result.streamInfo is not None
        assert result.streamInfo.token is not None
        activewebsession.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)
        result:AvStream = activewebsession.helper.dynamic_call(StreamSession.define_stream_for,
                                                   streamType=AVStreamType.CHANNEL,
                                                   streamId=zender.id,
                                                   suppressHD=True)
        assert result is not None
        assert result.streamInfo is not None
        assert result.streamInfo.token is not None
        activewebsession.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)
        with pytest.raises((ValueError, WebException)):
            result:AvStream = activewebsession.helper.dynamic_call(StreamSession.define_stream_for,
                                                    streamType=999,
                                                    streamId=zender.id,
                                                    suppressHD=True)
        result:AvStream = activewebsession.helper.dynamic_call(StreamSession.define_stream_for,
                                                   streamType=AVStreamType.CHANNEL,
                                                   streamId='DOES_NOT_EXIST',
                                                   suppressHD=True)
        assert result == b''

    def test_recording_get_token(self,activewebsession):
        assert len(activewebsession.session.customerInfo) != 0
        activewebsession.session.get_entitlements()

        rl = RecordingList(activewebsession.addon)
        rl.refresh()
        seasons = rl.get_season_recordings(RecordingType.RECORDED)
        season: SeasonRecording = seasons[0]

        recordings = season.get_episodes(RecordingType.RECORDED)
        assert len(recordings) > 0, 'Please make sure there is at least one recording available for the test account'
        recording: Recording = recordings[0]
        assert recording is not None, 'Please make sure there is at least one recording available for the test account'
        print(f'First={recording.id}')
        result = activewebsession.helper.dynamic_call(StreamSession.define_stream,
                                                      streamItem=recording)
        assert result is not None
        assert result.streamInfo is not None
        assert result.streamInfo.token is not None
        activewebsession.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)

        result = activewebsession.helper.dynamic_call(StreamSession.define_stream_for,
                                          streamType=AVStreamType.RECORDING,
                                          streamId=recording.id)
        assert result is not None
        assert result.streamInfo is not None
        assert result.streamInfo.token is not None
        activewebsession.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)

    def test_event_get_token(self, activewebsession):
        activewebsession.session.get_entitlements()
        activewebsession.session.refresh_channels()

        guide = ChannelGuide(activewebsession.addon, activewebsession.session.get_channels())
        guide.load_stored_events()

        for channel in activewebsession.session.get_channels():
            channel.events = guide.get_events(channel.id)

        startDate = datetime.datetime.now()
        endDate = startDate + datetime.timedelta(hours=2)
        guide.obtain_events_in_window(startDate.astimezone(datetime.timezone.utc),
                                      endDate.astimezone(datetime.timezone.utc))
        channel: Channel = activewebsession.session.get_channels()[0]
        channel.events = guide.get_events(channel.id)
        event = channel.events.get_current_event()
        assert event is not None, 'Cannot find event'
        if not event.hasDetails:
            try:
                event.details = activewebsession.helper.dynamic_call(
                    activewebsession.session.get_event_details, eventId=event.id)
                assert event.id == event.details.eventId
            # pylint: disable=broad-exception-caught
            except Exception as we:
                print(f'Could not get the details for this event, this may happen sometimes: {we}')
        result = activewebsession.helper.dynamic_call(StreamSession.define_stream,
                                                      streamItem=event)
        assert result is not None
        assert result.streamInfo is not None
        assert result.streamInfo.token is not None
        activewebsession.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)

        result = activewebsession.helper.dynamic_call(StreamSession.define_stream_for,
                                          streamType=AVStreamType.EVENT,
                                          streamId=event.id)
        assert result is not None
        assert result.streamInfo is not None
        assert result.streamInfo.token is not None
        activewebsession.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)

    def test_vod_get_token(self,activewebsession):
        activewebsession.session.get_entitlements()

        response = activewebsession.helper.dynamic_call(activewebsession.session.obtain_vod_screens)
        screens = response['screens']
        screen = screens[0]

        movies = MovieList(activewebsession.addon, screen['id'])
        movie: Movie
        for movie in movies.movies:
            movies.update_details(movie)
            playableInstance, _ = movie.asset.find_entitled_offer(OfferType.FREE)
            if movie.asset.goPlayable and playableInstance:
                print(f'Found playable movie: {movie.asset.title}')
                break

        assert movie is not None
        assert playableInstance is not None
        result = activewebsession.helper.dynamic_call(StreamSession.define_stream,
                                                      streamItem=playableInstance)
        assert result is not None
        assert result.streamInfo is not None
        assert result.streamInfo.token is not None
        activewebsession.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)

        result = activewebsession.helper.dynamic_call(StreamSession.define_stream_for,
                                                      streamType=AVStreamType.VOD,
                                                      streamId=playableInstance.id)
        assert result is not None
        assert result.streamInfo is not None
        assert result.streamInfo.token is not None
        activewebsession.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)
