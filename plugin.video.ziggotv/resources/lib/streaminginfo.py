"""
Contains classes to hold streaming info, including token, for different types
"""
import dataclasses


@dataclasses.dataclass
class StreamingInfo:
    """
    Base Class containing streaming info
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, streamingJson):
        self.registrationRequired = streamingJson['deviceRegistrationRequired']
        self.drmContentId = streamingJson['drmContentId']
        self.isAdult = False
        if 'isAdult' in streamingJson:
            self.isAdult = streamingJson['isAdult']
        self.token = None


@dataclasses.dataclass
class ReplayStreamingInfo:
    # pylint: disable=too-many-instance-attributes
    def __init__(self, streamingJson):
        self.registrationRequired = streamingJson['deviceRegistrationRequired']
        self.drmContentId = streamingJson['drmContentId']
        if 'licenceDurationSeconds' in streamingJson:
            self.licenseDurationSeconds = streamingJson['licenceDurationSeconds']
        else:
            self.licenseDurationSeconds = -1
        self.endTime = streamingJson['eventSessionEndTime']
        self.startTime = streamingJson['eventSessionStartTime']
        self.prePaddingTime = streamingJson['prePaddingTime']
        self.postPaddingTime = streamingJson['postPaddingTime']
        self.thumbnailUrl = streamingJson['thumbnailServiceUrl']
        self.isAdult = False
        if 'isAdult' in streamingJson:
            self.isAdult = streamingJson['isAdult']
        self.ageRating = -1
        if 'ageRating' in streamingJson:
            self.ageRating = streamingJson['ageRating']
        self.fallbackUrl = streamingJson['fallbackUrl']
        self.url = streamingJson['url']
        self.isAvad = streamingJson['isAvad']
        self.trickPlayControl = []
        if 'trickPlayControl' in streamingJson:
            self.trickPlayControl = streamingJson['trickPlayControl']
        self.token = None

    @property
    def fast_forward_allowed(self):
        return 'disallowFastForward' not in self.trickPlayControl

    @property
    def skip_forward_allowed(self):
        return 'disallowSkipForward' not in self.trickPlayControl

    @property
    def ad_restriction(self):
        return 'adRestrictionOnly' not in self.trickPlayControl

@dataclasses.dataclass
class VodStreamingInfo:
    # pylint: disable=too-many-instance-attributes
    def __init__(self, streamingJson):
        self.registrationRequired = streamingJson['deviceRegistrationRequired']
        self.drmContentId = streamingJson['drmContentId']
        self.displayProviderName = streamingJson['displayProviderName']
        self.displayProvider = streamingJson['displayProvider']
        self.contentProviderName = streamingJson['contentProviderName']
        self.contentProvider = streamingJson['contentProvider']
        self.thumbnailUrl = streamingJson['thumbnailServiceUrl']
        self.url = streamingJson['url']
        if 'licenceDurationSeconds' in streamingJson:
            self.licenseDurationSeconds = streamingJson['licenceDurationSeconds']
        else:
            self.licenseDurationSeconds = -1
        self.token = None


@dataclasses.dataclass
class RecordingStreamingInfo:
    # pylint: disable=too-many-instance-attributes
    def __init__(self, streamingJson):
        self.registrationRequired = streamingJson['deviceRegistrationRequired']
        self.trickPlayControl = streamingJson['trickPlayControl']
        self.thumbnailUrl = streamingJson['thumbnailServiceUrl']
        self.eventSessionStartTime = streamingJson['eventSessionStartTime']
        self.eventSessionEndTime = streamingJson['eventSessionEndTime']
        self.prePaddingTime = streamingJson['prePaddingTime']
        self.postPaddingTime = streamingJson['postPaddingTime']
        self.drmContentId = streamingJson['drmContentId']
        self.isAvad = streamingJson['isAvad']
        self.actualProgramStartOffset = streamingJson['actualProgramStartOffset']
        self.url = streamingJson['url']
        self.fallbackUrl = streamingJson['fallbackUrl']
        self.token = None
