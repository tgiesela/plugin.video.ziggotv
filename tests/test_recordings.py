# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

import datetime
import unittest

from resources.lib.channel import ChannelList, Channel
from resources.lib.channelguide import ChannelGuide
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.recording import RecordingList, SingleRecording, SeasonRecording, PlannedRecording
from resources.lib.webcalls import LoginSession
from tests.test_base import TestBase
import xbmcgui
import xbmc

class TestRecordings(TestBase):

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)

    def print_recordings(self, recs: RecordingList):
        self.do_login()
        if isinstance(recs, RecordingList):
            print('#: {0}, size: {1}, quota: {2}, used: {3}'.format(recs.total,
                                                                    recs.size,
                                                                    recs.quota,
                                                                    recs.occupied))
            for rec in recs.recs:
                if isinstance(rec, SingleRecording):
                    print('Single {0}: {1}'.format(rec.title, rec.recordingState))
                elif isinstance(rec, PlannedRecording):
                    print('Planned {0}: {1}'.format(rec.title, rec.recordingState))
                elif isinstance(rec, SeasonRecording):
                    season: SeasonRecording = rec
                    print('Season {0} #: {1}'.format(season.title, season.episodes))
                    for episode in season.get_episodes('planned'):
                        print(season.title + ' ' + episode.startTime)
                    for episode in season.get_episodes('recorded'):
                        print(season.title + ' ' + episode.startTime)
        else:
            for rec in recs:
                if isinstance(rec, SingleRecording):
                    print('Single {0}: {1}'.format(rec.title, rec.recordingState))
                elif isinstance(rec, PlannedRecording):
                    print('Planned {0}: {1}'.format(rec.title, rec.recordingState))
                elif isinstance(rec, SeasonRecording):
                    print('Season recording not expected here')

    def test_planned(self):
        self.do_login()
        self.session.refresh_recordings(True)
        recs = self.session.get_recordings_planned()
        self.print_recordings(recs)
        for rec in recs.recs:
            if isinstance(rec, SeasonRecording):
                print('SHOW ' + rec.title + '\n')
                season: SeasonRecording = rec
                for episode in season.episodes:
                    print(season.title + ' ' + episode.startTime)

    def test_recorded(self):
        self.do_login()
        self.session.refresh_recordings(True)
        recs = self.session.get_recordings_recorded()
        self.print_recordings(recs)

    def test_record(self):
        self.do_login()
        self.session.refresh_channels()
        self.session.refresh_entitlements()
        self.session.refresh_recordings(True)
        recs = self.session.get_recordings_recorded()
        self.assertIsNotNone(recs)
        self.print_recordings(recs)
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
        self.session.refresh_recordings(True)
        recs = self.session.get_recordings_recorded()
        self.print_recordings(recs)
        recs = self.session.get_recordings_planned()
        self.print_recordings(recs)
        rslt = self.session.delete_recordings(event=windowEvents[0].id)
        print(rslt)
        rslt = self.session.delete_recordings(event=windowEvents[1].id)
        print(rslt)

    def test_getdetails(self):
        self.do_login()
        self.session.refresh_recordings(True)
        recs = self.session.get_recordings_recorded()
        listitemhelper = ListitemHelper(self.addon)
        for rec in recs.recs:
            if isinstance(rec, SeasonRecording):
                for recording in rec.episodes:
                    li = listitemhelper.listitem_from_recording(recording)
                    print(li.getLabel())
                continue
            else:
                details = self.session.get_recording_details(recordingId=rec.id)
                li = listitemhelper.listitem_from_recording(rec)
                print(li.getLabel())
            print(details)

    def test_kanweg(self):
        self.do_login()

        self.session.refresh_recordings(True)
        recordings_recorded: RecordingList = self.session.get_recordings_recorded()
        recordings_planned: RecordingList = self.session.get_recordings_planned()

        recording: SeasonRecording = None
        for recording in recordings_recorded.get_season_recordings():
            print(f'SHOW {recording.title} rectype: {recording.type}\n')
        recording: SingleRecording = None
        for recording in recordings_recorded.get_recorded_recordings():
            if isinstance(recording, (SingleRecording)):
                print(f'SINGLE {recording.title} rectype: {recording.type}\n')
            else:
                for recording in recordings_planned.get_planned_recordings():
                    if isinstance(recording, (SingleRecording)):
                        print('NOT EXPECTED')
                    else:
                        print(f'PLANNED {recording.title} rectype: {recording.type}\n')



if __name__ == '__main__':
    unittest.main()
