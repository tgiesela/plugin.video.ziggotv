# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

import datetime
from time import sleep

from resources.lib import utils
from resources.lib.channel import SavedChannelsList
from resources.lib.recording import SavedStateList

class TestUtils:
    TIMERCOUNT = 0
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.tmr: utils.TimeSignal
    #     self.tmrRuns = False
    #     self.timercount = 0

    def timer_func(self):
        print(f"Timer_expired: count={self.TIMERCOUNT}")
        self.TIMERCOUNT += 1

    def test_times(self):
        rslt = utils.DatetimeHelper.to_unix('2021-06-03T18:01:16.974Z', '%Y-%m-%dT%H:%M:%S.%fZ')
        assert rslt == 1622736076

        rslt = utils.DatetimeHelper.to_unix('2026-01-05T15:50:00Z', '%Y-%m-%dT%H:%M:%SZ')
        print(rslt)
        startTime = utils.DatetimeHelper.from_unix(
            utils.DatetimeHelper.to_unix('2021-06-03T18:01:16.974Z', '%Y-%m-%dT%H:%M:%S.%fZ'))
        assert '2021-06-03' == startTime.strftime('%Y-%m-%d')
        assert '18:01' == startTime.strftime('%H:%M')

        startTime = utils.DatetimeHelper.from_unix(
            utils.DatetimeHelper.to_unix('2025-12-31T21:20:00.000Z', '%Y-%m-%dT%H:%M:%S.%fZ'))
        newtime = utils.DatetimeHelper.from_utc_to_local(startTime)
        assert '2025-12-31' == newtime.strftime('%Y-%m-%d')
        assert '22:20' == newtime.strftime('%H:%M')

    def test_timer(self):
        tmr = utils.TimeSignal(5, self.timer_func)
        tmr.start()
        #self.tmrRuns = True
        sleep(12)
        tmr.stop()
        tmr.join()
        tmr = utils.TimeSignal(10, self.timer_func)
        tmr.start()
        #self.tmrRuns = True
        sleep(2)
        tmr.stop()
        tmr.join()

        # stopTmr = utils.Timer(20, self.timer_stopit)
        # stopTmr.start()
        # while self.tmrRuns:
        #     sleep(1)
        # stopTmr.stop()


class TestSavedStates:
    def test_states(self, activewebsession):
        recList = SavedStateList(activewebsession.addon)
        recList.add('crid:~~2F~~2Fgn.tv~~2F817615~~2FSH010806510000~~2F237133469,'
                    'imi:517366be71fa5106c9215d9f1367cbacef4a4772', 350.000)
        assert len(recList.states) == 1
        recList.add('crid:~~2F~~2Fgn.tv~~2F817615~~2FSH010806510000~~2F237133469,'
                    'imi:517366be71fa5106c9215d9f1367cbacef4a4772', 400.000)
        assert len(recList.states) == 1
        recList.add('crid:~~2F~~2Fgn.tv~~3F817615~~2FSH010806510000~~2F237133469,'
                    'imi:517366be71fa5106c9215d9f1367cbacef4a4772', 350.000)
        assert len(recList.states) == 2
        recList.delete('unknown')
        assert len(recList.states) == 2
        recList.delete('crid:~~2F~~2Fgn.tv~~2F817615~~2FSH010806510000~~2F237133469,'
                       'imi:517366be71fa5106c9215d9f1367cbacef4a4772')
        assert len(recList.states) == 1
        sleep(1)
        recList.cleanup(0)
        assert len(recList.states) == 0
        recList = SavedStateList(activewebsession.addon)
        assert len(recList.states) == 0
        recList.cleanup()
        assert len(recList.states) == 0

    def test_saved_channels(self, activewebsession):
        savedchannels = SavedChannelsList(activewebsession.addon)
        savedchannels.states = {'NL_000001_019401':
            {'name': 'NPO-1',
             'datePlayed': utils.DatetimeHelper.unix_datetime(datetime.datetime.now())}}
        savedchannels.save()
        savedchannels = SavedChannelsList(activewebsession.addon)
        savedchannels.states = {}
        savedchannels.save()
        savedchannels = SavedChannelsList(activewebsession.addon)
        savedchannels.add('NL_000001_019401', 'NPO-1')
        assert len(savedchannels.states) == 1
        savedchannels.add('NL_000003_019405', 'NPO-3')
        assert len(savedchannels.states) == 2
        savedchannels.add('NL_000005_019462', 'RTL-5')
        assert len(savedchannels.states) == 3
        savedchannels.delete('NL_000005_019462')
        assert len(savedchannels.states) == 2
        sleep(1)
        savedchannels.cleanup(0,1)
        assert len(savedchannels.states) == 1
        savedchannels = SavedChannelsList(activewebsession.addon)
        savedchannels.cleanup()

# if __name__ == '__main__':
#     unittest.main()
