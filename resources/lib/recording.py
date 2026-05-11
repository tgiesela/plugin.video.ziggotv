"""
module containing classes for recordings
"""
import dataclasses
import datetime
from enum import IntEnum
import json
from pathlib import Path

import xbmcaddon
import xbmcvfs
import xbmc

from resources.lib import utils
from resources.lib.globals import G
from resources.lib.savedstates import BaseSavedStateList
from resources.lib.webcalls import LoginSession


@dataclasses.dataclass
class Poster:
    """
    Small data class to store the poster
    """

    def __init__(self, posterJson):
        self.url = posterJson['url']
        self.type = posterJson['type']  # values seen: HighResPortrait



class RecordingType(IntEnum):
    """
    Enum for the service status
    """
    PLANNED = 1
    RECORDED = 2

class Recording:
    """
    class to store all the data for a recording. Is used as a base class for others.
    """

    # pylint: disable=too-many-instance-attributes
    @dataclasses.dataclass
    class Language:
        """
        small class to store the data for a language
        """

        def __init__(self, languageJson):
            self.language = languageJson['lang']
            self.purpose = languageJson['purpose']

    def __init__(self, recordingJson):
        # pylint: disable=too-many-branches, too-many-statements
        if 'poster' in recordingJson:
            self.poster = Poster(posterJson=recordingJson['poster'])
        else:
            self.poster = None
        self.recordingState = recordingJson['recordingState']  # recorded, planned
        self.minimumAge = 0
        self.private = False
        self.isAdult = False
        self.diskSpace = 0
        self.expirationDate = ''
        self.technicalDuration = 0
        self.isOttBlackout = False
        self.duration = 0
        self.bookmark = 0
        self.subtitles = []
        self.seasonNumber = None
        self.episodeNumber = None
        self.type = 'undefined'
        if 'type' in recordingJson:
            self.type = recordingJson['type']
        if 'episodeTitle' in recordingJson:
            self.episodeTitle = recordingJson['episodeTitle']
        self.synopsis = ''
        if 'synopsis' in recordingJson:
            self.synopsis = recordingJson['synopsis']

        if 'captionLanguages' in recordingJson:
            for subtitle in recordingJson['captionLanguages']:
                self.subtitles.append(self.Language(subtitle))
        self.audioLanguages = []
        if 'audioLanguages' in recordingJson:
            for subtitle in recordingJson['audioLanguages']:
                self.audioLanguages.append(self.Language(subtitle))
        self.ottMarkers = []
        if 'ottMarkers' in recordingJson:
            self.ottMarkers = recordingJson['ottMarkers']
        self.channelId = None
        if 'channelId' in recordingJson:
            self.channelId = recordingJson['channelId']  # NL_000001_019401
        self.prePaddingOffset = recordingJson['prePaddingOffset']  # 300
        self.postPaddingOffset = recordingJson['postPaddingOffset']  # 900
        self.recordingType = recordingJson['recordingType']  # nDVR
        self.showId = None
        if 'showId' in recordingJson:
            self.showId = recordingJson['showId']  # crid:~~2F~~2Fgn.tv~~2F817615~~2FSH010806510000
        self.title = None
        if 'title' in recordingJson:
            self.title = recordingJson['title']
        self.startTime = recordingJson['startTime']  # 2024-01-17T11:00:00.000Z
        self.endTime = recordingJson['endTime']  # 2024-01-17T11:16:00.000Z
        self.source = recordingJson['source']  # single
        if 'id' in recordingJson:
            self.id = recordingJson['id']  # crid:~~2F~~2Fgn.tv~~2F817615~~2FSH010806510000~~2F237133469,
            # imi:517366be71fa5106c9215d9f1367cbacef4a4772
        else:
            self.id = recordingJson['episodeId']
        # self.type = recordingjson['type']  # single or season
        if 'ottPaddingsBlackout' in recordingJson:
            self.ottPaddingsBlackout = recordingJson['ottPaddingsBlackout']  # false
        else:
            if 'isOttBlackout' in recordingJson:
                self.ottPaddingsBlackout = recordingJson['isOttBlackout']  # false
        if 'isPremiereAirings' in recordingJson:
            self.isPremiereAirings = recordingJson['isPremiereAirings']  # false
        else:
            self.isPremiereAirings = False
        if 'deleteTime' in recordingJson:
            self.deleteTime = recordingJson['deleteTime']  # 2025-01-16T11:16:00.000Z
        else:
            self.deleteTime = recordingJson['expirationDate']  # ???
        if 'retentionPeriod' in recordingJson:
            self.retentionPeriod = recordingJson['retentionPeriod']  # 365
        else:
            self.retentionPeriod = 0
        if 'autoDeletionProtected' in recordingJson:
            self.autoDeletionProtected = recordingJson['autoDeletionProtected']  # false
        else:
            self.autoDeletionProtected = False
        self.isPremiere = recordingJson['isPremiere']  # false, true: when latest episode playing
        self.trickPlayControl = []
        if 'trickPlayControl' in recordingJson:
            self.trickPlayControl = recordingJson['trickPlayControl']
        if 'episodeNumber' in recordingJson:
            self.episodeNumber = recordingJson['episodeNumber']
        if 'seasonNumber' in recordingJson:
            self.seasonNumber = recordingJson['seasonNumber']

    @property
    def isRecording(self) -> bool:
        """
        Returns True if the state of the Recording is recording or ongoing
        @return: True/False
        """
        return self.recordingState in ['recording', 'ongoing']

    @property
    def isPlanned(self):
        """
        Returns True if the state of the Recording is planned
        @return: True/False
        """
        return self.recordingState == 'planned'

    @property
    def isRecorded(self):
        """
        Returns True if the state of the Recording is recorded
        @return: True/False
        """
        return self.recordingState in ['recorded','ongoing']

class SeasonRecording:
    """
    class for season/series recording
    It is a container for recordings which belong to a series/season. It is not a single recording itself.
    The recordings itself are stored in the episodes attribute and can be of type PlannedRecording or SingleRecording
    """

    # pylint: disable=too-many-instance-attributes, too-few-public-methods, too-many-branches, too-many-statements
    def __init__(self, recordingJson, recordingtype:RecordingType):
        self.poster = Poster(posterJson=recordingJson['poster'])
        self.recordingType = recordingtype
        self.title = recordingJson['title']
        self.source = recordingJson['source']
        self.nrofepisodes = recordingJson['noOfEpisodes']
        self.channelId = recordingJson['channelId']
        self.id = recordingJson['id']
        self.type = recordingJson['type']
        self.shortSynopsis = None
        if 'shortSynopsis' in recordingJson:
            self.shortSynopsis = recordingJson['shortSynopsis']
        self.genres = []
        if 'genres' in recordingJson:
            self.genres = recordingJson['genres']
        self.images = []
        if 'images' in recordingJson:
            self.images = recordingJson['images']
        self.seasons = []
        if 'seasons' in recordingJson:
            self.seasons = recordingJson['seasons']

        if self.type in ['season','show']:
            self.seasonTitle = None
            if 'seasonTitle' in recordingJson:
                self.seasonTitle = recordingJson['seasonTitle']
            self.showId = None
            if 'showId' in recordingJson:
                self.showId = recordingJson['showId']
            self.minimumAge = 0
            if 'minimumAge' in recordingJson:
                self.minimumAge = recordingJson['minimumAge']
            self.diskSpace = 0
            if 'diskSpace' in recordingJson:
                self.diskSpace = recordingJson['diskSpace']
            self.isPremiereAirings = False
            if 'isPremiereAirings' in recordingJson:
                self.isPremiereAirings = recordingJson['isPremiereAirings']
            self.relevantEpisode = None
            if 'mostRelevantEpisode' in recordingJson:
                self.relevantEpisode = recordingJson['mostRelevantEpisode']
            self.episodes = []
            if 'episodes' in recordingJson:
                episodes = recordingJson['episodes']
                self.cnt = 0
                if 'total' in episodes:
                    self.cnt = episodes['total']
                self.episodes = []
                for episode in episodes['data']:
                    if episode['recordingState'] == 'planned':
                        recPlanned = PlannedRecording(episode, self)
                        self.episodes.append(recPlanned)
                    else:
                        recSingle = SingleRecording(episode, self)
                        self.episodes.append(recSingle)
        else:
            self.episodes = []
            self.showId = self.id

    def get_episodes(self, recType: RecordingType):
        """

        @param recType: one 'planned|recorded'
        @return: list of requested types
        """
        retList = []
        episode: Recording = None
        for episode in self.episodes:
            if recType == RecordingType.PLANNED:
                if episode.recordingState == 'planned':
                    retList.append(episode)
            else:
                if episode.recordingState != 'planned':
                    retList.append(episode)
        return retList


class SingleRecording(Recording):
    """
    class for a SingleRecording (not planned, not season).
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, recordingJson, season: SeasonRecording = None):
        super().__init__(recordingJson)
        if 'privateCopy' in recordingJson:
            self.private = recordingJson['privateCopy']
        else:
            self.private = False
        self.isAdult = recordingJson['containsAdult']
        if '' in recordingJson:
            self.diskSpace = recordingJson['diskSpace']  # 0.041527778
        else:
            self.diskSpace = 0
        self.technicalDuration = recordingJson['technicalDuration']
        self.isOttBlackout = False
        if 'isOttBlackout' in recordingJson:
            self.isOttBlackout = recordingJson['isOttBlackout']  # false
        self.duration = recordingJson['duration']  # 598,
        self.bookmark = recordingJson['bookmark']  # 0
        self.viewState = recordingJson['viewState']  # notWatched
        self.season: SeasonRecording = season
        if self.season is not None:
            if self.channelId is None:
                self.channelId = self.season.channelId
            if self.showId is None:
                self.showId = self.season.showId
            if self.title is None:
                self.title = self.season.title


class PlannedRecording(Recording):
    """
    class for a planned recording (not a season or single recording).
    """

    def __init__(self, recordingJson, season: SeasonRecording = None):
        super().__init__(recordingJson)
        self.minimumAge = 0
        if 'minimumAge' in recordingJson:
            self.minimumAge = recordingJson['minimumAge']
        self.viewState = 'notWatched'
        self.season: SeasonRecording = season
        if season is not None:
            if self.channelId is None:
                self.channelId = self.season.channelId
            if self.showId is None:
                self.showId = self.season.showId
            if self.title is None:
                self.title = self.season.title


class RecordingList:
    """
    container class for a list of recordings of any type
    """
    # pylint: disable=too-few-public-methods, too-many-instance-attributes
    def __init__(self, addon: xbmcaddon.Addon):
        self.addon = addon
        self.helper = utils.ProxyHelper(addon)
        self.recs = []
        self.total = 0
        self.quota = 0
        self.size = 0
        self.occupied = 0
        self.recordingDetails = {}

        self.file = xbmcvfs.translatePath(self.addon.getAddonInfo('profile')) + G.RECORDINGS_INFO
        self.__load_and_parse()

    def __load_and_parse(self):
        """
        function to load the recordings details from file and parse it to fill the recordings list
        @return:
        """
        if Path(self.file).exists():
            self.recs = []
            self.total = 0
            self.quota = 0
            self.size = 0
            recordings = json.loads(Path(self.file).read_text(encoding='utf-8'))
            self.__parse(recordings['planned'], RecordingType.PLANNED)
            self.__parse(recordings['recorded'], RecordingType.RECORDED)

    def __parse(self, recordingsJson, recordingtype: str):

        self.total += recordingsJson['total']
        self.size += recordingsJson['size']
        self.quota += recordingsJson['quota']['quota']
        self.occupied = recordingsJson['quota']['occupied']
        for data in recordingsJson['data']:
            if data['type'] in ['season', 'show']:
                season = SeasonRecording(data, recordingtype)
                self.recs.append(season)
            elif data['type'] == 'single':
                if data['recordingState'] == 'planned':
                    recPlanned = PlannedRecording(data)
                    self.recs.append(recPlanned)
                else:
                    recSingle = SingleRecording(data)
                    self.recs.append(recSingle)

    def __save_recordings_details(self):
        """
        Function to save the captured details of a series
        
        :param self: 
        """
        Path(self.file).write_text(json.dumps(self.recordingDetails), encoding='utf-8')

    def save(self):
        """
        Save all captured detailed information
        
        :param self: Description
        """
        self.__save_recordings_details()

    def cleanup(self):
        """
        clean/remove all captured detailed information
        
        :param self: Description
        """
        self.recordingDetails = []
        self.__save_recordings_details()
        self.__load_and_parse()

    def find(self, eventId):
        """
        function to find a recording by its id
        @param eventId:
        @return: recording
        """
        for rec in self.recs:
            if isinstance(rec, SeasonRecording):
                season: SeasonRecording = rec
                for srec in season.episodes:
                    if srec.id == eventId:
                        return srec
            else:
                recording: Recording = rec
                if recording.id == eventId:
                    return rec
        return None

    def get_planned_recordings(self):
        """
        function to get all planned recordings
        @return: list of planned recordings
        """
        plannedRecs = []
        for rec in self.recs:
            if isinstance(rec, PlannedRecording) and rec.isPlanned:
                recording: PlannedRecording = rec
                if recording.isPlanned:
                    plannedRecs.append(recording)
        return plannedRecs

    def get_recorded_recordings(self) -> list:
        """
        function to get all recorded recordings
        @return: list of recorded recordings
        """
        recordedRecs = []
        for rec in self.recs:
            if isinstance(rec, SingleRecording) and rec.isRecorded:
                recording: SingleRecording = rec
                if recording.isRecorded:
                    recordedRecs.append(recording)
        return recordedRecs

    def get_all_recordings(self):
        """
        function to get all recordings
        @return: list of all recordings
        """
        allRecs = []
        for rec in self.recs:
            if isinstance(rec, SeasonRecording):
                season: SeasonRecording = rec
                for srec in season.episodes:
                    allRecs.append(srec)
            elif isinstance(rec, SingleRecording):
                recording: SingleRecording = rec
                allRecs.append(recording)
            elif isinstance(rec, PlannedRecording):
                recording: PlannedRecording = rec
                allRecs.append(recording)
        return allRecs

    def get_season_recordings(self, rectype: RecordingType):
        """
        function to get all season recordings, i.e. recordings of type SeasonRecording
        a season recording is a container for multiple recordings of a series/season
        @return: list of season recordings
        """
        seasonRecs = []
        for rec in self.recs:
            if isinstance(rec, SeasonRecording) and rec.recordingType == rectype:
                season: SeasonRecording = rec
                seasonRecs.append(season)
        return seasonRecs

    def sort_listitems(self, listing: list, sortby: int, sortorder: int):
        """
        Function to sort a list of ListItems
        
        :param self: 
        :param listing: list of listitems
        :type listing: list
        :param sortby: the key to sort on
        :type sortby: int
        :param sortorder: the order in which to sort 
        :type sortorder: int
        """
        if int(sortby) == utils.SharedProperties.TEXTID_NAME:
            if int(sortorder) == utils.SharedProperties.TEXTID_ASCENDING:
                listing.sort(key=lambda x: x.getLabel().lower())
            else:
                listing.sort(key=lambda x: x.getLabel().lower(), reverse=True)
        elif int(sortby) == utils.SharedProperties.TEXTID_NUMBER:
            # We do not sort on number for recordings
            pass
        elif int(sortby) == utils.SharedProperties.TEXTID_DATE:
            if int(sortorder) == utils.SharedProperties.TEXTID_ASCENDING:
                listing.sort(key=lambda x: int(x.getVideoInfoTag().getUniqueID('ziggoRecordingId')))
            else:
                listing.sort(key=lambda x: int(x.getVideoInfoTag().getUniqueID('ziggoRecordingId')), reverse=True)

    def refresh(self):
        """
        function to refresh the recordings list by reloading the details from file and re-parsing it
        @return:
        """
        recordings = self.helper.dynamic_call(LoginSession.refresh_recordings,
                                              includeAdult=self.addon.getSettingBool('adult-allowed'))
        self.recordingDetails = recordings
        self.__save_recordings_details()
        self.__load_and_parse()

    def delete_recording(self, plannedrec: Recording):
        """
        function to delete a recording
        @param recording: the recording to delete
        @return:
         """
        if plannedrec.isPlanned:
            self.helper.dynamic_call(LoginSession.delete_recordings_planned,
                                    event=plannedrec.id,
                                    show=None,
                                    channelId=plannedrec.channelId)
        else:
            self.helper.dynamic_call(LoginSession.delete_recordings,
                                    event=plannedrec.id,
                                    show=None,
                                    channelId=plannedrec.channelId)
        for rec in self.recs:
            if isinstance(rec, SeasonRecording):
                season: SeasonRecording = rec
                for seasonrec in season.episodes:
                    if seasonrec.id == plannedrec.id:
                        season.episodes.remove(seasonrec)
                        xbmc.log("Episode with id {0} deleted".format(seasonrec.id), xbmc.LOGDEBUG)
            elif isinstance(rec, SingleRecording):
                singlerec: SingleRecording = rec
                if singlerec.id == plannedrec.id:
                    self.recs.remove(singlerec)
                    xbmc.log("Recording with id {0} deleted".format(seasonrec.id), xbmc.LOGDEBUG)
            elif isinstance(rec, PlannedRecording):
                bookedrec: PlannedRecording = rec
                if bookedrec.id == plannedrec.id:
                    self.recs.remove(bookedrec)
                    xbmc.log("Planned recording with id {0} deleted".format(seasonrec.id), xbmc.LOGDEBUG)

    def __can_delete_whole_season(self, season: SeasonRecording, deleteBookedAndRecorded: bool):
        """
        function to check if a whole season recording can be deleted
        @param season: the season recording to check
        @param deleteBookedAndRecorded: whether to delete booked and recorded episodes
        @return: True if the season recording can be deleted, False otherwise
        """
        # Implementation for checking if the whole season can be deleted
        plannedEpisodes = season.get_episodes(RecordingType.PLANNED)
        recordedEpisodes = season.get_episodes(RecordingType.RECORDED)
        if deleteBookedAndRecorded:
            return True
        if season.recordingType == RecordingType.PLANNED:
            if len(recordedEpisodes) == 0:
                return True
        elif season.recordingType == RecordingType.RECORDED:
            if len(plannedEpisodes) == 0:
                return True
        return False

    def delete_season_recording(self, season: SeasonRecording, deleteBookedAndRecorded: bool):
        """
        function to delete a season recording
        @param recording: the season recording to delete
        @return:
        """
        if season.showId is not None:
            showId = season.showId
        else:
            showId = season.id

        if not self.__can_delete_whole_season(season, deleteBookedAndRecorded):
            # This means that we only want to delete the recordings of the current season type,
            # i.e. only the planned episodes or only the recorded episodes, and keep the season recording itself.
            #
            # Unfortunately the API does not support to delete only the recorded season recordings (afaik)
            # or only the planned season recordings, i.e. we cannot delete the season recording as a whole
            # So we need to delete the single recordings one by one
            episode: Recording = None
            for episode in season.episodes:
                if season.recordingType == RecordingType.PLANNED and episode.isPlanned:
                    self.delete_recording(episode)
                elif season.recordingType == RecordingType.RECORDED and episode.isRecorded:
                    self.delete_recording(episode)
        else:
            if season.recordingType == RecordingType.PLANNED:
                self.helper.dynamic_call(LoginSession.delete_recordings_planned,
                                        show=showId,
                                        channelId=season.channelId)
                # With the current API there is no need to delete the recordings, because they
                # are automatically deleted when the planned season recording is deleted, but we do it anyway to be sure
                # to delete all recordings of the season, including the recorded ones
                self.helper.dynamic_call(LoginSession.delete_recordings,
                                    show=showId,
                                    channelId=season.channelId)
            else:
                self.helper.dynamic_call(LoginSession.delete_recordings,
                                    show=showId,
                                    channelId=season.channelId)
                # With the current API there is no need to delete the plannedrecordings, because they
                # are automatically deleted when the season recording is deleted, but we do it anyway to be sure
                # to delete all recordings of the season, including the recorded ones
                self.helper.dynamic_call(LoginSession.delete_recordings_planned,
                                    show=showId,
                                    channelId=season.channelId)
            self.recs.remove(season)
        xbmc.log(f"Recording of complete show with id {season.showId} deleted", xbmc.LOGDEBUG)

class SavedStateList(BaseSavedStateList):
    """
    class to keep the list of recordings/movies which are currently being played. 
    This is used to stop the playback of a recording/movie when it is deleted from 
    the recordings list, and to prevent that a recording/movie is deleted while it 
    is being played.
    """

    def __init__(self, addon: xbmcaddon.Addon):
        fileName = G.PLAYBACK_INFO
        super().__init__(addon, fileName)

    def add(self, itemId, position):
        """
        function to add/update the position of a recording
        @param itemId:
        @param position:
        @return:
        """
        self.states.update({itemId: {'position': position,
                                     'dateAdded': utils.DatetimeHelper.unix_datetime(datetime.datetime.now())}})
        self.save()

    def get_position(self, itemId):
        """
        function to find a position of a recording by its id
        @param itemId:
        @return:
        """
        item = super().get(itemId)
        if item is not None:
            return item['position']
        return None
