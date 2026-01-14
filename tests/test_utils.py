# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

import datetime
import unittest
from time import sleep

from resources.lib import utils
from resources.lib.channel import SavedChannelsList
from resources.lib.recording import SavedStateList
from tests.test_base import TestBase


class TestUtils(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tmr: utils.TimeSignal
        self.tmrRuns = False
        self.timercount = 0

    def timer_stopit(self):
        self.tmr.stop()
        print("Other timer stopped")
        self.tmrRuns = False

    def timer_func(self):
        print(f"Timer_expired: count={self.timercount}")
        self.timercount += 1

    def test_times(self):
        rslt = utils.DatetimeHelper.to_unix('2021-06-03T18:01:16.974Z', '%Y-%m-%dT%H:%M:%S.%fZ')
        self.assertEqual(rslt, 1622736076)

        rslt = utils.DatetimeHelper.to_unix('2026-01-05T15:50:00Z', '%Y-%m-%dT%H:%M:%SZ')
        print(rslt)
        startTime = utils.DatetimeHelper.from_unix(utils.DatetimeHelper.to_unix('2021-06-03T18:01:16.974Z', '%Y-%m-%dT%H:%M:%S.%fZ'))
        self.assertEqual('2021-06-03', startTime.strftime('%Y-%m-%d'))
        self.assertEqual('18:01', startTime.strftime('%H:%M'))
        
        startTime = utils.DatetimeHelper.from_unix(utils.DatetimeHelper.to_unix('2025-12-31T21:20:00.000Z', '%Y-%m-%dT%H:%M:%S.%fZ'))
        newtime = utils.DatetimeHelper.from_utc_to_local(startTime)
        self.assertEqual('2025-12-31', newtime.strftime('%Y-%m-%d'))
        self.assertEqual('22:20', newtime.strftime('%H:%M'))

    def test_timer(self):
        self.tmr = utils.TimeSignal(5, self.timer_func)
        self.tmr.start()
        #self.tmrRuns = True
        sleep(12)
        self.tmr.stop()
        self.tmr.join()
        self.tmr = utils.TimeSignal(10, self.timer_func)
        self.tmr.start()
        #self.tmrRuns = True
        sleep(2)
        self.tmr.stop()
        self.tmr.join()

        # stopTmr = utils.Timer(20, self.timer_stopit)
        # stopTmr.start()
        # while self.tmrRuns:
        #     sleep(1)
        # stopTmr.stop()


class TestSavedStates(TestBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.do_login()

    def test_states(self):
        recList = SavedStateList(self.addon)
        recList.add('crid:~~2F~~2Fgn.tv~~2F817615~~2FSH010806510000~~2F237133469,'
                    'imi:517366be71fa5106c9215d9f1367cbacef4a4772', 350.000)
        recList.add('crid:~~2F~~2Fgn.tv~~2F817615~~2FSH010806510000~~2F237133469,'
                    'imi:517366be71fa5106c9215d9f1367cbacef4a4772', 400.000)
        recList.add('crid:~~2F~~2Fgn.tv~~3F817615~~2FSH010806510000~~2F237133469,'
                    'imi:517366be71fa5106c9215d9f1367cbacef4a4772', 350.000)
        recList.delete('unknown')
        recList.delete('crid:~~2F~~2Fgn.tv~~2F817615~~2FSH010806510000~~2F237133469,'
                       'imi:517366be71fa5106c9215d9f1367cbacef4a4772')
        recList.cleanup(0)
        recList = SavedStateList(self.addon)
        recList.cleanup()

    def test_saved_channels(self):
        savedchannels = SavedChannelsList(self.addon)
        savedchannels.add('NL_000001_019401', 'NPO-1')
        savedchannels.add('NL_000003_019405', 'NPO-3')
        savedchannels.add('NL_000005_019462', 'RTL-5')
        savedchannels.delete('NL_000005_019462')
        savedchannels.cleanup(0,1)
        self.assertEqual(len(savedchannels.get_all()),2)
        savedchannels = SavedChannelsList(self.addon)
        savedchannels.cleanup()


if __name__ == '__main__':
    unittest.main()
