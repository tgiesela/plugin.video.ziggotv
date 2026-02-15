# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

import datetime
import unittest

from resources.lib.channel import ChannelList, Channel
from resources.lib.channelguide import ChannelGuide
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.recording import RecordingList, RecordingType, SingleRecording, SeasonRecording, PlannedRecording
from tests.test_base import TestBase

class TestRecordings(TestBase):

    def print_recordings(self, recs, rectype: RecordingType):
        for rec in recs:
            if isinstance(rec, SingleRecording):
                print('Single {0}: {1}'.format(rec.title, rec.recordingState))
            elif isinstance(rec, PlannedRecording):
                print('Planned {0}: {1}'.format(rec.title, rec.recordingState))
            elif isinstance(rec, SeasonRecording):
                season: SeasonRecording = rec
                print('Season {0} #: {1}'.format(season.title, len(season.episodes)))
                for episode in season.get_episodes(rectype):
                    print(season.title + ' ' + episode.startTime)

    def test_planned(self):
        self.do_login()
        self.logon_via_proxy()
        recordings: RecordingList = RecordingList(self.addon)
        recordings.refresh()
        recs = recordings.get_planned_recordings()
        self.print_recordings(recs, RecordingType.PLANNED)
        for rec in recs:
            if isinstance(rec, SeasonRecording):
                print('SHOW ' + rec.title + '\n')
                season: SeasonRecording = rec
                for episode in season.episodes:
                    print(season.title + ' ' + episode.startTime)

    def test_recorded(self):
        self.do_login()
        self.logon_via_proxy()
        # self.session.refresh_recordings(True)
        recordings: RecordingList = RecordingList(self.addon)
        recordings.refresh()
        recs = recordings.get_recorded_recordings()
        self.print_recordings(recs, RecordingType.RECORDED)
        recs = recordings.get_season_recordings(RecordingType.RECORDED)
        self.print_recordings(recs, RecordingType.RECORDED)

    def test_record(self):
        self.do_login()
        self.logon_via_proxy()
        self.session.refresh_channels()
        self.session.refresh_entitlements()
        # self.session.refresh_recordings(True)
        recordings: RecordingList = RecordingList(self.addon)
        recordings.refresh()
        recs = recordings.get_recorded_recordings()
        self.assertIsNotNone(recs)
        self.print_recordings(recs, RecordingType.RECORDED)
        epg = ChannelGuide(self.addon, self.session.get_channels())
        epg.load_stored_events()
        epg.obtain_events()
        channels = ChannelList(self.session.get_channels(), self.session.get_entitlements())
        npo1: Channel = None
        for channel in channels:
            if channel.name == 'NPO 1':
                npo1 = channel
                break
        self.assertIsNotNone(npo1)
        npo1.events = epg.get_events(npo1.id)
        # currentEvent = npo1.events.getCurrentEvent()
        windowEvents = npo1.events.get_events_in_window(datetime.datetime.now(),
                                                        datetime.datetime.now() + datetime.timedelta(hours=2))
        self.assertTrue(len(windowEvents) >= 2)
        rec1 = self.session.record_event(windowEvents[0].id)
        print(rec1)
        rec2 = self.session.record_event(windowEvents[1].id)
        print(rec2)
        # self.session.refresh_recordings(True)
        recordings: RecordingList = RecordingList(self.addon)
        recordings.refresh()
        recs = recordings.get_recorded_recordings()
        self.print_recordings(recs, RecordingType.RECORDED)
        recs = recordings.get_planned_recordings()
        self.print_recordings(recs, RecordingType.PLANNED)
        rslt = self.session.delete_recordings(event=windowEvents[0].id)
        print(rslt)
        rslt = self.session.delete_recordings(event=windowEvents[1].id)
        print(rslt)

    def test_getdetails(self):
        self.do_login()
        self.logon_via_proxy()
        # self.session.refresh_recordings(True)
        self.session.refresh_recordings(True)
        recordings: RecordingList = RecordingList(self.addon)
        recordings.refresh()
        recs = recordings.get_season_recordings(RecordingType.RECORDED)
        recs.extend(recordings.get_recorded_recordings())
        listitemhelper = ListitemHelper(self.addon)
        for rec in recs:
            if isinstance(rec, SeasonRecording):
                print(f'SEASON: {rec.title}')
                for recording in rec.get_episodes(RecordingType.RECORDED):
                    _ = listitemhelper.listitem_from_recording(recording)
                    if hasattr(recording, 'episodeTitle'):
                        episode = f'E{recording.episodeNumber}-{recording.episodeTitle}'
                    else:
                        if hasattr(recording, 'episodeNumber'):
                            episode = f'S{recording.seasonNumber}-E{recording.episodeNumber}'
                        else:
                            episode = f'S{recording.seasonNumber}-E?'
                    print(f'\tEPISODE: {episode}' )
                continue
            else:
                details = self.session.get_recording_details(recordingId=rec.id)
                _ = listitemhelper.listitem_from_recording(rec)
                print(f'SINGLE: {rec.title}' )
            print(details)

        recs = recordings.get_season_recordings(RecordingType.PLANNED)
        recs.extend(recordings.get_recorded_recordings())
        listitemhelper = ListitemHelper(self.addon)
        for rec in recs:
            if isinstance(rec, SeasonRecording):
                print(f'SEASON: {rec.title}')
                for recording in rec.get_episodes(RecordingType.PLANNED):
                    li = listitemhelper.listitem_from_recording(recording)
                    if hasattr(recording, 'episodeTitle'):
                        episode = f'E{recording.episodeNumber}-{recording.episodeTitle}'
                    else:
                        if hasattr(recording, 'episodeNumber'):
                            episode = f'S{recording.seasonNumber}-E{recording.episodeNumber}'
                        else:
                            episode = f'S{recording.seasonNumber}-E?'
                    print(f'\tEPISODE: {episode}' )
                continue
            else:
                details = self.session.get_recording_details(recordingId=rec.id)
                li = listitemhelper.listitem_from_recording(rec)
                print(f'SINGLE: {rec.title}' )
            print(details)


if __name__ == '__main__':
    unittest.main()
