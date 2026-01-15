"""
Module containiner helper classes for movies and series
"""
import json
from pathlib import Path
from enum import IntEnum
import xbmc
import xbmcaddon
import xbmcvfs

from resources.lib.events import Event
from resources.lib.globals import G
from resources.lib.utils import ProxyHelper
from resources.lib.webcalls import LoginSession

class GridLink:
    """
    class containing the gridLink Information. Used to display icon/poster 
    """
    def __init__(self, gridlinkJson):
        self.id         = gridlinkJson['id']
        self.type       = gridlinkJson['type']
        self.title      = gridlinkJson['title']
        self.theme      = gridlinkJson['theme']

class Offer:
    """
    class containing the offer information of an instance which could be played.
    """
    def __init__(self, offer):
        self.id = offer['id']
        self.type = offer['type']
        self.edsProductId = None
        if 'edsProductId' in offer:
            self.edsProductId = offer['edsProductId']
        self.name = offer['name']
        self.price = offer['price']
        self.priceDisplay = offer['priceDisplay']
        self.currency = offer['currency']
        self.relationAvailabilityStart = None
        if 'relationAvailabilityStart' in offer:
            self.relationAvailabilityStart = offer['relationAvailabilityStart']
        self.relationAvailabilityEnd = None
        if 'relationAvailabilityEnd' in offer:
            self.relationAvailabilityEnd = offer['relationAvailabilityEnd']
        self.entitled = offer['entitled']

class Instance:
    """
    class containing of instance from which we can choose to play the movie/episode
    """
    def __init__(self, instance):
        self.id = instance['id']
        self.resolution = instance['resolution']
        self.encodingProfile = instance['encodingProfile']
        self.isDolby = instance['isDolby']
        self.audioLang = instance['audioLang']
        self.subtiles = []
        if 'subtitles' in instance:
            self.subtitles = instance['subtitles']
        self.availabilityStart = instance['availabilityStart']
        self.availabilityEnd = instance['availabilityEnd']
        self.brandingProviderId = instance['brandingProviderId']
        self.isVodOttOnlyPurchasable = instance['isVodOttOnlyPurchasable']
        self.goPlayable = instance['goPlayable']
        self.goDownloadable = instance['goDownloadable']
        self.isAdEnabled = instance['isAdEnabled']
        self.isA2AEnabled = instance['isA2AEnabled']
        self.supportedExternalStreamingProtocols = []
        if 'supportedExternalStreamingProtocols' in instance:
            self.supportedExternalStreamingProtocols = instance['supportedExternalStreamingProtocols']
        self.offers: list[Offer] = []
        for offer in instance['offers']:
            self.offers.append(Offer(offer))

    def get_free_offer(self) -> Offer:
        """
        Search of an offer which is free and user is entitled
        
        :param self:
        :return: the found offer or None
        :rtype: Offer
        """
        for offer in self.offers:
            if offer.entitled is True:
                return offer
        return None

    def get_payed_offer(self) -> Offer:
        """
        Search of an offer which is not free and the user has to pay (not supported in this addon)
        
        :param self:
        :return: the found offer or None
        :rtype: Offer
        """
        for offer in self.offers:
            if offer.entitled is False:
                # Just to be sure: check pricing
                if float(offer.price) != 0:
                    return offer
        return None


class OfferType(IntEnum):
    """
    Enumeration of types to search for within instance/offer
    """
    FREE = 1,
    PAYED = 2

class Asset:
    """
    Class containing shared properties for movies and episodes
    """

    def __init__(self, info):
        self.id                 = info['id']
        self.type               = info['type']
        self.assetType          = info['assetType']
        self.isAdult            = info['isAdult']
        self.image              = G.STATIC_URL + 'image-service/intent/{crid}/posterTile'.format(crid=self.id)
        self.mergedId           = None
        if 'mergedId' in info:
            self.mergedId = info['mergedId']
        self.title = ''
        if 'title' in info:
            self.title = info['title']
        self.synopsis = ''
        if 'synopsis' in info:
            self.synopsis = info['synopsis']
        self.isAdult = info['isAdult']
        self.ageRating = info['ageRating']
        self.duration = 0
        if 'duration' in info:
            self.duration = info['duration']
        self.minResolution = None
        if 'minResolution' in info:
            self.minResolution = info['minResolution']
        self.genres = []
        if 'genres' in info:
            self.genres = info['genres']
        self.goPlayable = True
        if 'goPlayable' in info:
            self.goPlayable = info['goPlayable']
        # self.brandingProviderId already set
        self.prodYear = None
        if 'prodYear' in info:
            self.prodYear = info['prodYear']
        self.isPreview = info['isPreview']
        self.onWatchlist = info['onWatchlist']
        self.minimumAgeWarnings = []
        if 'minimumAgeWarnings' in info:
            self.minimumAgeWarnings = info['minimumAgeWarnings']
        self.audioLanguages = []
        if 'audioLanguages' in info:
            self.audioLanguages = info['audioLanguages']
        self.country = []
        if 'country' in info:
            self.country = info['country']
        if 'subtitles' in info:
            self.subtitles = info['subtitles']
        self.icons = []
        if 'icons' in info:
            self.icons = info['icons']
        self.castAndCrew = []
        if 'castAndCrew' in info:
            self.castAndCrew = info['castAndCrew']
        self.goPlayableViaExternalApp = True
        if 'goPlayableViaExternalApp' in info:
            self.goPlayableViaExternalApp = info['goPlayableViaExternalApp']
        self.instances: list[Instance] = []
        if 'instances' in info:
            for instance in info['instances']:
                self.instances.append(Instance(instance))

    def find_entitled_offer(self, offertype: OfferType = OfferType.FREE):
        """
        Function to search for an offer for which the user is entitled
        Depending on offertype, it will search for a free offer or a payed offer
        
        :param self: 
        :param offertype: type of offer to search for (payed or free)
        :type offertype: OfferType
        """
        if offertype == OfferType.FREE:
            for instance in self.instances:
                if instance.goPlayable:
                    offer = instance.get_free_offer()
                    if offer is not None:
                        return instance, offer
        elif offertype == OfferType.PAYED:
            for instance in self.instances:
                if instance.goPlayable:
                    offer = instance.get_payed_offer()
                    if offer is not None:
                        return instance, offer
        return None, None


class Movie:
    """
    class containing movie information
    """
    def __init__(self, movieJson):
        self.hasdetails         = False
        self.asset:Asset        = None
        self.id                 = movieJson['id'] # Also present in Asset
        self.ageRating          = movieJson['ageRating']
        self.brandingProviderId = None
        if 'brandingProviderId' in movieJson:
            self.brandingProviderId = movieJson['brandingProviderId']
        self.gridlink           = None
        if 'gridLink' in movieJson:
            self.gridlink:GridLink  = GridLink(movieJson['gridLink'])
        self.trailerInfo = []
        self.trailers = []

    def add_details(self, details):
        """
        Function add details originating from a webcall to the movie
        
        :param self: 
        :param details: the details in json format
        """
        self.hasdetails = True
        self.asset              = Asset(details)
        if details['id'] != self.id:
            raise RuntimeError('Details do not belong to this movie')
        if 'trailerInfo' in details:
            self.trailerInfo = details['trailerInfo']
        if 'trailers' in details:
            self.trailers = details['trailers']

    @property
    def image(self):
        """
        property to get the image
        
        :param self: Description
        """
        if self.asset is None:
            if self.gridlink is None:
                return G.STATIC_URL + 'image-service/intent/{crid}/posterTile'.format(crid=self.id)
            elif 'background' in self.gridlink.theme:
                return self.gridlink.theme['background']
        else:
            return self.asset.image

    @property
    def title(self):
        """
        Property to get the title
        
        :param self: Description
        """
        if self.asset is None:
            if self.gridlink is None:
                return f'<{self.id}>'
            else:
                return self.gridlink.title
        else:
            return self.asset.title

class Series:
    """
    class containing information of a series. 
    container must be a reference to a SeriesList
    """
    def __init__(self, seriesJson, container):
        self.serieslist         = container
        self.hasdetails         = False
        self.id                 = seriesJson['id']
        self.type               = seriesJson['type']
        self.assetType          = seriesJson['assetType']
        self.isAdult            = seriesJson['isAdult']
        self._title              = ''
        if 'title' in seriesJson:
            self._title             =seriesJson['title']
        if 'image' in seriesJson:
            self.image              = seriesJson['image']
        else:
            self.image              = G.STATIC_URL + 'image-service/intent/{crid}/posterTile'.format(crid=self.id)
        self.seriesId           = self.id
        if 'seriesId' in seriesJson:
            self.seriesId           = seriesJson['seriesId']
        self.brandingProviderId = None
        if 'brandingProviderId' in seriesJson:
            self.brandingProviderId = seriesJson['brandingProviderId']
        self.gridlink           = None
        if 'gridLink' in seriesJson:
            self.gridlink:GridLink  = GridLink(seriesJson['gridLink'])
        self.goPlayable         = False
        if 'goPlayable' in seriesJson:
            self.goPlayable         = seriesJson['goPlayable']

        # Details initialization
        self.genres: list[str] = []
        self.ageRating = None
        self.synopsis = ''
        self.startYear = None
        self.endYear = None
        self.seasonCount = 0
        self.mergedId = None
        self.seasons:list[Season] = []

    @property
    def title(self):
        """
        Property to get the title
        
        :param self: Description
        """
        if self._title is None or self._title == '':
            if self.gridlink.title is None or self.gridlink.title == '':
                return '<?>'
            return self.gridlink.title
        else:
            return self._title

    def add_details(self, seriesJson):
        """
        Adds seasons of a series
        
        :param self: 
        :param seriesJson: json data containing the details
        """
        if seriesJson['id'] != self.id:
            raise RuntimeError('Details do not belong to this series')

        self.hasdetails = True
        self._title  = seriesJson['title']
        self.genres = []
        if 'genres' in seriesJson:
            self.genres = seriesJson['genres']
        self.ageRating = seriesJson['ageRating']
        self.isAdult = seriesJson['isAdult']
        self.synopsis = seriesJson['synopsis']
        if 'startYear' in seriesJson:
            self.startYear = seriesJson['startYear']
        if 'endYear' in seriesJson:
            self.endYear = seriesJson['endYear']
        self.seasonCount = seriesJson['seasonCount']
        self.mergedId = seriesJson['mergedId']
        self.seasons:list[Season] = []
        if 'seasons' in seriesJson:
            for season in seriesJson['seasons']:
                self.seasons.append(Season(season, self))

    def find_season(self, seasonId):
        """
        Function to lookup up a season based on its id.
        
        :param self: 
        :param seasonId: Description
        """
        for season in self.seasons:
            if season.id == seasonId:
                return season
        return None

class Season:
    """
    class containing information of a season of a series. 
    """
    def __init__(self, seasonsJson, series: Series):
        self.series = series
        self.id = seasonsJson['id']
        self.title = seasonsJson['title']
        self.totalEpisodes = seasonsJson['totalEpisodes']
        self.seasonnumber = seasonsJson['season']
        self.episodes: list[Episode] = []
        for episode in seasonsJson['episodes']:
            self.episodes.append(Episode(episode, self))

    def find_episode(self, episodeId: str):
        """
        Function to lookup an episode based on its id
        
        :param self: 
        :param episodeId: Description
        :type episodeId: str
        """
        for episode in self.episodes:
            if episode.id == episodeId:
                return episode
        return None

class Episode:
    """
    class containing information of an episode of a series. 
    """
    class Source:
        """
        Class containing information about the source of an episode. 
        Can be an Event/Channel (linear) or a series/episode
        """
        def __init__(self, sourceType:str, source):
            self.entitlementState = None
            self.brandingProviderId = None
            self.titleId = source['titleId']
            self.imageVersion = source['imageVersion']
            self.ageRating = source['ageRating']
            self.duration = source['duration']
            self.sourceType = sourceType
            if sourceType.lower() == 'linear':
                self.type = sourceType
                self.goDownloadable = False
                self.broadcastDate = source['broadcastDate']
                self.channel = source ['channel']
                self.eventId = source['eventId']
            else:
                self.type = source['type']
                self.entitlementState = source['entitlementState']
                self.brandingProviderId = source['brandingProviderId']
                self.isGoPlayable = source['isGoPlayable']
                self.audioQuality = source['audioQuality']
                self.goDownloadable = source['goDownloadable']

    def __init__(self, episodeJson, season: Season):
        self.season             = season
        self.hasdetails         = False
        self.id                 = episodeJson['id']
        self.image              = G.STATIC_URL + 'image-service/intent/{crid}/posterTile'.format(crid=self.id)
        self.episodenumber      = episodeJson['episode']
        self.ageRating          = episodeJson['ageRating']
        self.synopsis           = episodeJson['synopsis']
        self.isAdult            = episodeJson['isAdult']
        self.type               = episodeJson['type']
        self.sourceType         = episodeJson['sourceType']
        self.source = self.Source(self.sourceType, episodeJson['source'])
        self.imageVersion       = episodeJson['imageVersion']
        self.mergedId           = None
        if 'mergedId' in episodeJson:
            self.mergedId           = episodeJson['mergedId']
        self.asset:Asset        = None
        if 'assetDetails' in episodeJson:
            self.add_details(episodeJson['assetDetails'])

    @property
    def title(self):
        """
        Property to get the title
        
        :param self: Description
        """
        if self.asset.title is None or self.asset.title == '':
            if self.season.title is None or self.season.title == '':
                title = f'{self.season.series.title} (S{self.season.seasonnumber}-E{self.episodenumber})'
            else:
                title = f'{self.season.title} (S{self.season.seasonnumber}-E{self.episodenumber})'
            return title
        else:
            return self.asset.title

    @property
    def brandingProviderId(self) -> str:
        """
        Helper function to get the brandingProviderId needed for some webcalls
        
        :param self: 
        :return: the brandingProviderId
        :rtype: str
        """
        return self.source.brandingProviderId

    # pylint: disable=invalid-name
    def isEvent(self) -> bool:
        """
        Function to determin if item is an Event instead of a episode
        
        :param self: 
        """

        return str(self.source.sourceType).lower() == 'linear'

    def add_details(self, info):
        """
        Add detailed information received from the webinterface
        
        :param self: 
        :param info: the json data received from the webinterface
        """
        self.hasdetails         = True
        self.asset              = Asset(info)

class SeriesList:
    """
    Class to obtain and hold infomation of avaiable series belonging to a specific 'screen'
    A 'screen' is a group defined by Ziggo to show in their web-interface.
    Details will only be obtained on request (get_details) and will be stored on disk for future use
    This is done to avoid to many calls when loading all available series. 
    When get_details is called, the information stored on disk will be updated with the latest
    information.
    If details are already available, these can be used for display purposed. For playing an item 
    it is recommended to always call get_details shortly before playing the item.
    """
    def __init__(self, addon: xbmcaddon.Addon, screenId:str):
        self.helper = ProxyHelper(addon)
        self.series: list[Series] = []
        self.addon: xbmcaddon.Addon = addon
        self.parseerrors = 0
        self.file = xbmcvfs.translatePath(self.addon.getAddonInfo('profile')) + G.SERIES_INFO
        self.seriesDetails = self.__load_series_details()
        self.__process_series(screenId)

    def __save_series_details(self):
        """
        Function to save the captured details of a series
        
        :param self: 
        """
        Path(self.file).write_text(json.dumps(self.seriesDetails), encoding='utf-8')

    def __del__(self):
        Path(self.file).write_text(json.dumps(self.seriesDetails), encoding='utf-8')

    def __process_series(self, screenId):
        itemsSeen = []
        screenDetails = self.helper.dynamic_call(LoginSession.obtain_vod_screen_details, collectionId=screenId)
        self.parseerrors = 0
        if 'collections' in screenDetails:
            for collection in screenDetails['collections']:
                for item in collection['items']:
                    if item['id'] in itemsSeen:
                        continue
                    if item['type'] == 'SERIES':
                        try:
                            itemsSeen.append(item['id'])
                            serie:Series = Series(item, self)
                            self.series.append(serie)
                            for seriedetails in self.seriesDetails:
                                if seriedetails['id'] == serie.id:
                                    serie.add_details(seriedetails)
                                    break
                        except KeyError as exc:
                            itemid=item['id']
                            xbmc.log(f'item: {item}',xbmc.LOGDEBUG)
                            xbmc.log(f'Parsing of series failed, for item-id: {itemid}, Exception{exc}',xbmc.LOGERROR)
                            self.parseerrors += 1

    def update_season_details(self, serie: Series):
        """
        Function to update the details of a season with episodes
        
        :param self: 
        :param serie: the series
        :type serie: Series
        """
        for seriedetails in self.seriesDetails:
            if seriedetails['id'] == serie.id:
                self.seriesDetails.remove(seriedetails)
                break
        details = self.helper.dynamic_call(LoginSession.obtain_series_overview, seriesId=serie.id)
        if not 'seasons' in details:
            seasons = self.helper.dynamic_call(LoginSession.get_episode_list, item=serie.id)
            if seasons is not None:
                details.update({'seasons': seasons['seasons']})
            else:
                raise RuntimeError('Cannot obtain seasons/episodes!!')

        self.seriesDetails.append(details)
        try:
            serie.add_details(details)
            return 0
        except KeyError as exc:
            xbmc.log(f'details: {details}',xbmc.LOGDEBUG)
            xbmc.log(f'Parsing of details of series failed, for series-id: {serie.id}, Exception{exc}',xbmc.LOGERROR)
            return 1


    def update_episode_details(self, episode: Episode):
        """
        Function to update the details of a episode
        
        :param self: 
        :param episode: Description
        :type episode: Episode
        """
        season = episode.season
        series = season.series
        storeddetails = None
        for seriedetails in self.seriesDetails:
            if seriedetails['id'] == series.id:
                storeddetails = seriedetails
                break
        if storeddetails is None:
            raise RuntimeError(f'Cannot update non-existing series with id{series.id}')
        assetDetails = self.helper.dynamic_call(
            LoginSession.obtain_asset_details, assetId=episode.id, brandingProviderId=episode.brandingProviderId)
        for storedseason in storeddetails['seasons']:
            if storedseason['id'] == season.id:
                for storedepisode in storedseason['episodes']:
                    if storedepisode['id'] == episode.id:
                        storedepisode.update({'assetDetails': assetDetails})
                        break
                break
        try:
            episode.add_details(assetDetails)
            return 0
        except KeyError as exc:
            xbmc.log(f'assetDetails: {assetDetails}',xbmc.LOGDEBUG)
            xbmc.log(f'Parsing of details of episode failed, for series-id: {series.id}, Exception{exc}',xbmc.LOGERROR)
            return 1

    def find_serie(self, seriesId) -> Series:
        """
        Function to find a series based on its id
        
        :param self: Description
        :param seriesId: Description
        :return: Description
        :rtype: Series
        """
        for serie in self.series:
            if serie.id == seriesId:
                return serie

    def __load_series_details(self):
        """
        Function to load stored details of series
        
        :param self: Description
        """
        if Path(self.file).exists():
            seriesDetails = json.loads(Path(self.file).read_text(encoding='utf-8'))
        else:
            seriesDetails = []
        return seriesDetails

    def get_event(self,episode:Episode) -> Event:
        """
        Function to get the event details of an episode of type 'Event'
        
        :param self: 
        :param episode: the episode with type 'Event
        :type episode: Episode
        :return: the detailed event
        :rtype: Event
        """
        if not episode.isEvent():
            raise RuntimeError('Episodes source is not an Event')
        eventId = episode.source.eventId
        result = self.helper.dynamic_call(LoginSession.get_event_details, eventId=eventId)
        result.update({'id': eventId})
        event = Event(result)
        event.details = result
        return event

    def save(self):
        """
        Save all captured detailed information
        
        :param self: Description
        """
        self.__save_series_details()

    def cleanup(self):
        """
        clean/remove all captured detailed information
        
        :param self: Description
        """
        self.seriesDetails = []
        self.__save_series_details()

class MovieList:
    """
    Class to obtain and hold infomation of avaiable movies belonging to a specific 'screen'.
    A 'screen' is a group defined by Ziggo to show in their web-interface.
    Details will only be obtained on request (get_details) and will be stored on disk for future use
    This is done to avoid to many calls when loading all available series. 
    When get_details is called, the information stored on disk will be updated with the latest
    information.
    If details are already available, these can be used for display purposed. For playing an item 
    it is recommended to always call get_details shortly before playing the item.
    """
    def __init__(self, addon: xbmcaddon.Addon, screenId:str):
        self.helper = ProxyHelper(addon)
        self.movies: list[Movie] = []
        self.addon: xbmcaddon.Addon = addon
        self.parseerrors = 0
        self.file = xbmcvfs.translatePath(self.addon.getAddonInfo('profile')) + G.MOVIE_INFO
        self.moviesDetails = self.__load_movies_details()
        self.__process_movies(screenId)

    def __del__(self):
        Path(self.file).write_text(json.dumps(self.moviesDetails), encoding='utf-8')

    def __process_movies(self, screenId):
        """
        Function to get all the movies from a video on demand collection
        
        :param self: 
        :param screenId: id of the vod screen
        """
        itemsSeen = []
        screenDetails = self.helper.dynamic_call(LoginSession.obtain_vod_screen_details, collectionId=screenId)
        self.parseerrors = 0
        if 'collections' in screenDetails:
            for collection in screenDetails['collections']:
                for item in collection['items']:
                    if item['id'] in itemsSeen:
                        continue
                    if item['type'] == 'ASSET':
                        try:
                            itemsSeen.append(item['id'])
                            movie:Movie = Movie(item)
                            self.movies.append(movie)
                            for moviedetails in self.moviesDetails:
                                if moviedetails['id'] == movie.id:
                                    movie.add_details(moviedetails)
                                    break
                        except KeyError as exc:
                            itemid=item['id']
                            xbmc.log(f'item: {item}',xbmc.LOGDEBUG)
                            xbmc.log(f'Parsing of movies failed, for item-id: {itemid}, Exception{exc}',xbmc.LOGERROR)
                            self.parseerrors += 1

    def update_details(self, movie: Movie):
        """
        Function to get the most recent details of a movie
        
        :param self: 
        :param movie: the movie for which the details have to be fetched
        :type movie: Movie
        """
        for moviedetails in self.moviesDetails:
            if moviedetails['id'] == movie.id:
                self.moviesDetails.remove(moviedetails)
                break
        if movie.brandingProviderId is not None:
            details = self.helper.dynamic_call(LoginSession.obtain_asset_details, assetId=movie.id,
                                                brandingProviderId=movie.brandingProviderId)
        else:
            details = self.helper.dynamic_call(LoginSession.obtain_asset_details, assetId=movie.id)

        self.moviesDetails.append(details)

        try:
            movie.add_details(details)
            return 0
        except KeyError as exc:
            xbmc.log(f'details: {details}',xbmc.LOGDEBUG)
            xbmc.log(f'Parsing of details of series failed, for series-id: {movie.id}, Exception{exc}',xbmc.LOGERROR)
            return 1

    def find_movie(self, movieId) -> Movie:
        """
        Function to find a movie within the movie collection by its id
        
        :param self: 
        :param movieId: the id of the movie to search for
        :return: Movie
        :rtype: Movies
        """
        for movie in self.movies:
            if movie.id == movieId:
                return movie

    def __save_movie_details(self):
        Path(self.file).write_text(json.dumps(self.moviesDetails), encoding='utf-8')

    def __load_movies_details(self):
        if Path(self.file).exists():
            moviesDetails = json.loads(Path(self.file).read_text(encoding='utf-8'))
        else:
            moviesDetails = []
        return moviesDetails

    def save(self):
        """
        Function to save the collected details of movies
        
        :param self: Description
        """
        self.__save_movie_details()

    def cleanup(self):
        """
        clean/remove all captured detailed information
        
        :param self: Description
        """
        self.moviesDetails = []
        self.__save_movie_details()
