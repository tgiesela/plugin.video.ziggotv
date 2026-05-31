"""
module with classes for program events used for epg, replay and recording
"""
import datetime
from typing import List

from resources.lib import utils
from resources.lib.linkedlist import LinkedList, Node


# pylint: disable=too-many-instance-attributes, too-few-public-methods
class EventDetails:
    """
    class containing the details of an event
    """
    def __init__(self, eventJson):
        self.description = eventJson.get('shortDescription')
        self.description = eventJson.get('longDescription','')
        self.eventId = eventJson['eventId']
        self.channelId = eventJson['channelId']
        self.mergedId = eventJson.get('mergedId')
        self.seriesId = eventJson.get('seriesId')
        self.episode = eventJson.get('episodeNumber')
        self.season = eventJson.get('seasonNumber')
        self.episodeName = eventJson.get('episodeName')
        self.actors = eventJson.get('actors',[])
        self.genres = eventJson.get('genres',[])

    @property
    def isSeries(self) -> bool:
        """
        property indicating if event is a series/show or single program
        @return: True/False
        """
        return self.seriesId is not None


class Event:
    """
    class containing the basic properties of an event. See EventDetails for more information
    """
    # pylint: disable=too-many-branches
    def __init__(self, eventJson: dict):
        self.programDetails: EventDetails = None
        self.startTime = eventJson.get('startTime')
        self.endTime = eventJson.get('endTime')
        self.title = eventJson.get('title','')
        self.id = eventJson['id']
        self.mergedId = eventJson.get('mergedId')
        self.minimumAge = eventJson.get('minimumAge',0)
        self.isPlaceHolder = eventJson.get('isPlaceHolder',False)
        self.replayTVMinAge = eventJson.get('replayTVMinAge',0)
        self.hasReplayTV = eventJson.get('hasReplayTV',True)
        self.hasReplayTVOTT = eventJson.get('hasReplayTVOTT',True)
        self.hasStartOver = eventJson.get('hasStartOver',True)

    @property
    def duration(self):
        """
        Length of event in seconds
        @return: length of event in seconds
        """
        return self.endTime - self.startTime

    @property
    def hasDetails(self) -> bool:
        """
        Indicates if details are already available
        @return: True/False
        """
        return self.programDetails is not None

    @property
    def details(self) -> EventDetails:
        """
        Get the event details
        @return: details
        """
        return self.programDetails

    @details.setter
    def details(self, value):
        self.programDetails = EventDetails(value)

    @property
    def canReplay(self) -> bool:
        """
        Checks if event supports replay
        @return: True/False
        """
        now = utils.DatetimeHelper.unix_datetime(datetime.datetime.now())
        if self.isPlaying:
            return self.hasStartOver and self.hasReplayTV
        if self.endTime <= now:
            return self.hasStartOver and self.hasReplayTV
        return False

    @property
    def canRecord(self) -> bool:
        """
        Checks if event can be recorded
        @return: True/False
        """
        now = utils.DatetimeHelper.unix_datetime(datetime.datetime.now())
        if self.isPlaying:
            return True
        if self.endTime <= now:
            return False
        if self.startTime > now:
            return True
        return False

    @property
    def isPlaying(self) -> bool:
        """
        Checks if event is currently playing
        @return: True/False
        """
        now = utils.DatetimeHelper.unix_datetime(datetime.datetime.now())
        if self.startTime < now < self.endTime:
            return True
        return False


class EventList(LinkedList):
    """
    class containing the events sorted on start time. Linked List implementation.
    """
    def __is_duplicate(self, event: Event):
        currentNode: Node = self.head
        while currentNode is not None:
            currentEvent: Event = currentNode.data
            if currentEvent.startTime == event.startTime and currentEvent.endTime == event.endTime:
                return True
            currentNode = currentNode.next
        return False

    def __find_insert_location(self, event: Event):
        # The event list is ordered on startTime
        currentNode: Node = self.head
        while currentNode is not None:
            currentEvent: Event = currentNode.data
            if currentEvent.startTime > event.startTime:
                return currentNode
            currentNode = currentNode.next
        return currentNode

    def insert_event(self, event: Event):
        """
        Insert event in the linked list of events
        @param event:
        @return:
        """
        currentNode: Node = self.head
        if currentNode is None:  # Emtpy list
            self.insert_at_begin(event)
            return
        if self.__is_duplicate(event):
            return
        node = self.__find_insert_location(event)
        if node is None:
            self.insert_at_end(event)
        else:
            if node.data is None:
                node.data = event
            else:
                self.insert_before(node, event)

    def get_events_in_window(self, tstart: datetime.datetime, tend: datetime.datetime) -> List[Event]:
        """
        Get a list of events in a specific time window (from tstart until tend)
        @param tstart:
        @param tend:
        @return:
        """
        evtList: List[Event] = []
        evtNode = self.__find_event(tstart, tend)
        endTime = utils.DatetimeHelper.unix_datetime(tend)
        while evtNode is not None:
            evt: Event = evtNode.data
            if evt.startTime >= endTime:
                break
            evtList.append(evtNode.data)
            evtNode = evtNode.next
        return evtList

    def get_current_event(self) -> Event:
        """
        Get the current event playing
        @return: event | None
        """
        currentTime: datetime.datetime = utils.DatetimeHelper.unix_datetime(datetime.datetime.now())
        currentNode: Node = self.head
        while currentNode is not None:
            currentEvent: Event = currentNode.data
            if currentEvent.startTime <= currentTime <= currentEvent.endTime:
                return currentEvent
            if currentTime > currentEvent.endTime:
                currentNode = currentNode.next
            else:
                return None
        return None

    def get_next_event(self, current: Event) -> Event:
        """
        get the next event, based on the current event
        
        :param self: 
        :param current: the event from which to start
        :type current: Event
        :return: the next event or None
        :rtype: Event
        """
        currentNode: Node = self.head
        while currentNode is not None:
            currentEvent: Event = currentNode.data
            if currentEvent.id == current.id:
                if currentNode.next is None:
                    return None
                return currentNode.next.data
            currentNode = currentNode.next
        return None

    def __find_event(self, ts: datetime.datetime, te: datetime.datetime) -> Node:
        windowStartTime = utils.DatetimeHelper.unix_datetime(ts)
        windowEndTime = utils.DatetimeHelper.unix_datetime(te)
        currentNode: Node = self.head
        while currentNode is not None:
            currentEvent: Event = currentNode.data
            if windowStartTime >= currentEvent.startTime:  # start of event before start of window
                if currentEvent.endTime > windowStartTime:  # end of event beyond start of window
                    return currentNode
            if windowStartTime < currentEvent.startTime < windowEndTime:
                return currentNode
            if currentEvent.startTime >= windowStartTime:
                return None
            currentNode = currentNode.next
        return None
