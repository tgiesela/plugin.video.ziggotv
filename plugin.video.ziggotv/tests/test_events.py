import unittest
import datetime

from resources.lib import utils
from resources.lib.channel import ChannelGuide
from resources.lib.events import EventList
from tests.test_base import TestBase


class TestEvents(TestBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.do_login()

    def test_events(self):
        self.session.refresh_channels()

        guide = ChannelGuide(self.addon, self.session.get_channels())
        guide.loadStoredEvents()

        for channel in self.session.get_channels():
            channel.events = guide.getEvents(channel.id)

        startDate = datetime.datetime.now()
        endDate = startDate + datetime.timedelta(hours=2)
        guide.obtainEventsInWindow(startDate.astimezone(datetime.timezone.utc),
                                   endDate.astimezone(datetime.timezone.utc))

        for channel in self.session.get_channels():
            channel.events = guide.getEvents(channel.id)

        latestEndDate = endDate
        startDate = startDate + datetime.timedelta(days=-6)
        oldestStartDate = startDate
        endDate = startDate + datetime.timedelta(hours=2)
        guide.obtainEventsInWindow(startDate.astimezone(datetime.timezone.utc),
                                   endDate.astimezone(datetime.timezone.utc))
        startDate = startDate + datetime.timedelta(hours=6)
        endDate = startDate + datetime.timedelta(hours=2)
        guide.obtainEventsInWindow(startDate.astimezone(datetime.timezone.utc),
                                   endDate.astimezone(datetime.timezone.utc))
        guide.storeEvents()
        channels = []
        for channel in self.session.get_channels():
            channel.events = guide.getEvents(channel.id)
            events: EventList = channel.events
            if events is not None and events.head is not None:
                event = events.head.data
                event.details = self.session.get_event_details(event.id)
            channels.append(channel)

        for channel in channels:
            print('Channel id: {0}, name: {1}'.format(channel.id, channel.name))
            evts = channel.events.getEventsInWindow(oldestStartDate, latestEndDate)
            for evt in evts:
                print('    Event: {0}, duration: {1}, start: {2}, end: {3}'.format(
                    evt.title,
                    evt.duration,
                    utils.DatetimeHelper.fromUnix(evt.startTime).strftime('%y-%m-%d %H:%M'),
                    utils.DatetimeHelper.fromUnix(evt.endTime).strftime('%y-%m-%d %H:%M')))
            # evt = channel.events.__findEvent(datetime.datetime.now())
            # if evt is not None:
            #    print('    Current event: {0}: start: {1}, end: {2}'.format(evt.data.title
            #                                                                , evt.data.startTime
            #                                                               , evt.data.endTime))


if __name__ == '__main__':
    unittest.main()
