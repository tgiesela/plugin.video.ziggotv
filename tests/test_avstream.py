# pylint: disable=missing-function-docstring, missing-class-docstring, missing-module-docstring
import datetime

from resources.lib.avstream import AVStreamType, AvStream, StreamSession
from resources.lib.channel import Channel, ChannelList
from resources.lib.channelguide import ChannelGuide
from resources.lib.movies import Movie, MovieList, OfferType
from resources.lib.recording import Recording, RecordingList, RecordingType, SeasonRecording
from resources.lib.utils import ProxyHelper
from tests.test_base import TestBase


class TestAvStream(TestBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = ProxyHelper(self.addon)

    def test_channel_get_token(self):
        self.do_login()
        self.logon_via_proxy()
        self.assertFalse(len(self.session.customerInfo) == 0)

        self.session.refresh_channels()
        channels = self.session.get_channels()
        entitlements = self.session.get_entitlements()
        cl = ChannelList(channels, entitlements)
        zender:Channel = cl.find_channel_by_number(1)

        result:AvStream = self.helper.dynamic_call(StreamSession.define_stream,
                                                   streamItem=zender,
                                                   suppressHD=False)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.streamInfo)
        self.assertIsNotNone(result.streamInfo.token)
        self.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)

        result:AvStream = self.helper.dynamic_call(StreamSession.define_stream,
                                                   streamItem=zender,
                                                   suppressHD=True)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.streamInfo)
        self.assertIsNotNone(result.streamInfo.token)
        self.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)

        result:AvStream = self.helper.dynamic_call(StreamSession.define_stream_for,
                                                   streamType=AVStreamType.CHANNEL,
                                                   streamId=zender.id,
                                                   suppressHD=False)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.streamInfo)
        self.assertIsNotNone(result.streamInfo.token)
        self.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)
        result:AvStream = self.helper.dynamic_call(StreamSession.define_stream_for,
                                                   streamType=AVStreamType.CHANNEL,
                                                   streamId=zender.id,
                                                   suppressHD=True)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.streamInfo)
        self.assertIsNotNone(result.streamInfo.token)
        self.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)

    def test_recording_get_token(self):
        self.do_login()
        self.logon_via_proxy()
        self.assertFalse(len(self.session.customerInfo) == 0)
        self.session.get_entitlements()

        rl = RecordingList(self.addon)
        rl.refresh()
        seasons = rl.get_season_recordings(RecordingType.RECORDED)
        season: SeasonRecording = seasons[1]

        recordings = season.get_episodes(RecordingType.RECORDED)
        self.assertTrue(len(recordings) > 0,
                        'Please make sure there is at least one recording available for the test account')
        recording: Recording = recordings[0]
        self.assertIsNotNone(recording,
                             'Please make sure there is at least one recording available for the test account')
        print('First={0}'.format(recording.title))
        result = self.helper.dynamic_call(StreamSession.define_stream,
                                          streamItem=recording)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.streamInfo)
        self.assertIsNotNone(result.streamInfo.token)
        self.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)

        result = self.helper.dynamic_call(StreamSession.define_stream_for,
                                          streamType=AVStreamType.RECORDING,
                                          streamId=recording.id)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.streamInfo)
        self.assertIsNotNone(result.streamInfo.token)
        self.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)

    def test_event_get_token(self):
        self.do_login()
        self.logon_via_proxy()
        self.session.get_entitlements()
        self.session.refresh_channels()

        guide = ChannelGuide(self.addon, self.session.get_channels())
        guide.load_stored_events()

        for channel in self.session.get_channels():
            channel.events = guide.get_events(channel.id)

        startDate = datetime.datetime.now()
        endDate = startDate + datetime.timedelta(hours=2)
        guide.obtain_events_in_window(startDate.astimezone(datetime.timezone.utc),
                                      endDate.astimezone(datetime.timezone.utc))
        channel: Channel = self.session.get_channels()[0]
        channel.events = guide.get_events(channel.id)
        event = channel.events.get_current_event()
        self.assertIsNotNone(event,'Cannot find event')
        if not event.hasDetails:
            try:
                event.details = self.helper.dynamic_call(self.session.get_event_details, eventId=event.id)
                self.assertEqual(event.id, event.details.eventId)
            # pylint: disable=broad-exception-caught
            except Exception as we:
                print(f'Could not get the details for this event, this may happen sometimes: {we}')
        result = self.helper.dynamic_call(StreamSession.define_stream,
                                          streamItem=event)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.streamInfo)
        self.assertIsNotNone(result.streamInfo.token)
        self.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)

        result = self.helper.dynamic_call(StreamSession.define_stream_for,
                                          streamType=AVStreamType.EVENT,
                                          streamId=event.id)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.streamInfo)
        self.assertIsNotNone(result.streamInfo.token)
        self.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)

    def test_vod_get_token(self):
        self.do_login()
        self.logon_via_proxy()
        self.session.get_entitlements()

        response = self.helper.dynamic_call(self.session.obtain_vod_screens)
        screens = response['screens']
        screen = screens[0]

        movies = MovieList(self.addon, screen['id'])
        movie: Movie
        for movie in movies.movies:
            movies.update_details(movie)
            playableInstance, _ = movie.asset.find_entitled_offer(OfferType.FREE)
            if movie.asset.goPlayable and playableInstance:
                print(f'Found playable movie: {movie.asset.title}')
                break

        self.assertIsNotNone(movie)
        self.assertIsNotNone(playableInstance)
        result = self.helper.dynamic_call(StreamSession.define_stream,
                                          streamItem=playableInstance)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.streamInfo)
        self.assertIsNotNone(result.streamInfo.token)
        self.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)

        result = self.helper.dynamic_call(StreamSession.define_stream_for,
                                          streamType=AVStreamType.VOD,
                                          streamId=playableInstance.id)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.streamInfo)
        self.assertIsNotNone(result.streamInfo.token)
        self.helper.dynamic_call(StreamSession.stop_stream,streamid=result.id)
