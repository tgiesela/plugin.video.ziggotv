# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

import datetime

from resources.lib.channel import ChannelList, Channel
from resources.lib.channelguide import ChannelGuide
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.recording import RecordingList, RecordingType, SingleRecording, SeasonRecording, PlannedRecording

class TestRecordings:

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

    def test_planned(self, activewebsession):
        recordings: RecordingList = RecordingList(activewebsession.addon)
        recordings.refresh()
        recs = recordings.get_planned_recordings()
        self.print_recordings(recs, RecordingType.PLANNED)
        for rec in recs:
            if isinstance(rec, SeasonRecording):
                print('SHOW ' + rec.title + '\n')
                season: SeasonRecording = rec
                for episode in season.episodes:
                    print(season.title + ' ' + episode.startTime)

    def test_test(self, activewebsession):
        activewebsession.session.refresh_recordings(True)
        recordings: RecordingList = RecordingList(activewebsession.addon)
#        recordings.refresh()
        recs = recordings.get_planned_recordings()
        self.print_recordings(recs, RecordingType.PLANNED)
        recs = recordings.get_season_recordings(RecordingType.PLANNED)
        self.print_recordings(recs, RecordingType.PLANNED)

    def test_recorded(self, activewebsession):
        # self.session.refresh_recordings(True)
        recordings: RecordingList = RecordingList(activewebsession.addon)
        recordings.refresh()
        recs = recordings.get_recorded_recordings()
        self.print_recordings(recs, RecordingType.RECORDED)
        recs = recordings.get_season_recordings(RecordingType.RECORDED)
        self.print_recordings(recs, RecordingType.RECORDED)

    def test_record(self, activewebsession):
        activewebsession.session.refresh_channels()
        activewebsession.session.refresh_entitlements()
        entitlements = activewebsession.session.get_entitlements()
        assert entitlements is not None
        assert len(entitlements) > 0
        # self.session.refresh_recordings(True)
        recordings: RecordingList = RecordingList(activewebsession.addon)
        recordings.refresh()
        recs = recordings.get_recorded_recordings()
        assert recs is not None
        self.print_recordings(recs, RecordingType.RECORDED)
        epg = ChannelGuide(activewebsession.addon, activewebsession.session.get_channels())
        epg.load_stored_events()
        epg.obtain_events()
        channels = ChannelList(activewebsession.session.get_channels(),
                               entitlements)
        npo1: Channel = None
        for channel in channels:
            if channel.name == 'NPO 1':
                npo1 = channel
                break
        assert npo1 is not None
        npo1.events = epg.get_events(npo1.id)
        # currentEvent = npo1.events.getCurrentEvent()
        windowEvents = npo1.events.get_events_in_window(datetime.datetime.now(),
                                                        datetime.datetime.now() + datetime.timedelta(hours=2))
        assert len(windowEvents) >= 1
        rec1 = activewebsession.session.record_event(windowEvents[0].id)
        print(rec1)
        if len(windowEvents) > 1:
            rec2 = activewebsession.session.record_event(windowEvents[1].id)
            print(rec2)
        # activewebsession.session.refresh_recordings(True)
        recordings: RecordingList = RecordingList(activewebsession.addon)
        recordings.refresh()
        recs = recordings.get_recorded_recordings()
        self.print_recordings(recs, RecordingType.RECORDED)
        recs = recordings.get_planned_recordings()
        self.print_recordings(recs, RecordingType.PLANNED)
        rslt = activewebsession.session.delete_recordings(event=windowEvents[0].id)
        print(rslt)
        if len(windowEvents) > 1:
            rslt = activewebsession.session.delete_recordings(event=windowEvents[1].id)
            print(rslt)

    def test_getdetails(self, activewebsession):
        # self.session.refresh_recordings(True)
        activewebsession.session.refresh_recordings(True)
        recordings: RecordingList = RecordingList(activewebsession.addon)
        recordings.refresh()
        recs = recordings.get_season_recordings(RecordingType.RECORDED)
        recs.extend(recordings.get_recorded_recordings())
        listitemhelper = ListitemHelper(activewebsession.addon)
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
            details = activewebsession.session.get_recording_details(recordingId=rec.id)
            _ = listitemhelper.listitem_from_recording(rec)
            print(f'SINGLE: {rec.title}' )
            print(details)

        recs = recordings.get_season_recordings(RecordingType.PLANNED)
        recs.extend(recordings.get_recorded_recordings())
        listitemhelper = ListitemHelper(activewebsession.addon)
        for rec in recs:
            if isinstance(rec, SeasonRecording):
                print(f'SEASON: {rec.title}')
                for recording in rec.get_episodes(RecordingType.PLANNED):
                    li = listitemhelper.listitem_from_recording(recording)
                    assert li is not None
                    if hasattr(recording, 'episodeTitle'):
                        episode = f'E{recording.episodeNumber}-{recording.episodeTitle}'
                    else:
                        if hasattr(recording, 'episodeNumber'):
                            episode = f'S{recording.seasonNumber}-E{recording.episodeNumber}'
                        else:
                            episode = f'S{recording.seasonNumber}-E?'
                    print(f'\tEPISODE: {episode}' )
                continue
            details = activewebsession.session.get_recording_details(recordingId=rec.id)
            li = listitemhelper.listitem_from_recording(rec)
            print(f'SINGLE: {rec.title}' )
            print(details)


# if __name__ == '__main__':
#     unittest.main()
