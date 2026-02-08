"""
Module with functions to load movies/series window and the window class itself
"""
from enum import IntEnum
import os

import threading
import traceback
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from resources.lib.globals import S
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.movies import SeriesList, MovieList, Series, Season, Episode, Movie
from resources.lib.utils import ProxyHelper, WebException, check_service
from resources.lib.webcalls import LoginSession
from resources.lib.windows.basewindow import BaseWindow
from resources.lib import utils
class MovieWindow(BaseWindow):
    """
    window class for display movies and series
    """
    CHANNELBUTTON=5
    EPGBUTTON=6
    RECORDINGSBUTTON=7
    MOVIESBUTTON=8
    MOVIECATEGORIESLIST=150
    RECENTRECORDINGSLIST=250
    MOVIELIST=50
    class ScreenState(IntEnum):
        """
        Enumeration for the differen screen states
        """
        CATEGORY = 1,
        OVERVIEW = 2,
        SEASONS = 3,
        EPISODES = 4

    def __init__(self, xmlFilename, scriptPath, defaultSkin = "Default",
                 defaultRes = "720p", isMedia = False, addon=''):
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes, isMedia, addon)
        self.addon = addon
        self.movieList = None
        self.helper = ProxyHelper(self.addon)
        self.screens = None
        self.listitemHelper = ListitemHelper(self.addon)
        self.movieOverviews = []
        self.seriesOverviews = []
        self.addonpath = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        self.screenstate = self.ScreenState.CATEGORY
        self.currentcategoryId = None
        self.currentseasonId = None
        self.currentseriesId = None
        self.thread = None
        self.movies: MovieList = None
        self.series: SeriesList = None
        self.inepisodes = False
        self.inseasons = False
        self.playingListitem = None

    def __showmoviecategories(self):
        listing = []
        # this puts the focus on the first button of the screen
        # pylint: disable=no-member
        moviecategorieslist: xbmcgui.ControlList = self.getControl(self.MOVIECATEGORIESLIST)

        response = self.helper.dynamic_call(LoginSession.obtain_vod_screens)
        self.screens = response['screens']
#       logos in screen['brandLogoImage','logoNonfocused']

        if self.addon.getSettingBool('adult-allowed'):
            self.screens.append(response['hotlinks']['adultRentScreen'])
        for screen in self.screens:
            # Create a list item with a text label and a thumbnail image.
            listItem = xbmcgui.ListItem(label=screen['title'])
            # Set additional info for the list item.
            tag: xbmc.InfoTagVideo = listItem.getVideoInfoTag()
            tag.setTitle(screen['title'])
            tag.setMediaType('video')
            tag.setGenres([screen['title']])
            tag.setUniqueIDs({'ziggoCategoryId': screen['id']})

            iconurl = ''
            if 'theme' in screen:
                if 'brandLogoImage' in screen['theme']:
                    iconurl = screen['theme']['brandLogoImage']
                elif 'logoNonfocused' in screen['theme']:
                    iconurl = screen['theme']['logoNonfocused']
                elif 'background' in screen['theme']:
                    iconurl = screen['theme']['background']

            thumbname = xbmc.getCacheThumbName(iconurl)
            thumbfile = xbmcvfs.translatePath('special://thumbnails/' + thumbname[0:1] + '/' + thumbname)
            if os.path.exists(thumbfile):
                os.remove(thumbfile)
            listItem.setArt({'icon': iconurl,
                             'thumb': iconurl,
                             'poster': iconurl})

            listing.append(listItem)

        moviecategorieslist.reset()
        moviecategorieslist.addItems(listing)
        moviecategorieslist.selectItem(0)
        self.setFocusId(self.MOVIECATEGORIESLIST)

    def start_monitor(self, itemId):
        """
        Function to start a thread which can do monitoring of the position in the current playing item.
        The position will be saved and can be used to position the playing item at that position if required.
        
        :param self: 
        :param itemId: The id of the item to be monitored
        """
        self.videoHelper.requestorCallbackStop = self.play_stopped
        self.thread = threading.Thread(target=self.videoHelper.monitor_state,args=(itemId,))
        self.thread.start()

    def stop_monitor(self):
        """
        Function to stop the monitor
        
        :param self: 
        """
        if self.thread is not None:
            self.videoHelper.stop_player()
            self.thread.join()
            self.thread = None

    def play_stopped(self):
        """
        Method to be called when the player is stopped. It will reset the playing 
        listitem and stop the monitor thread if needed
        
        :param self: Description
        """
        self.videoHelper.requestorCallbackStop = None
        if self.playingListitem is not None:
            vod = self.__get_episode_or_movie(self.playingListitem)
            self.listitemHelper.updateresumepointinfo(self.playingListitem,
                                                      vod.id,
                                                      vod.asset.duration)
        self.stop_monitor()

    def __get_episode_or_movie(self, li: xbmcgui.ListItem):
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        movieid = tag.getUniqueID('ziggomovieid')
        episodeid = tag.getUniqueID('ziggoepisodeid')

        if episodeid is not None and episodeid != '':
            serie = self.series.find_serie(self.currentseriesId)
            season = serie.find_season(self.currentseasonId)
            vod:Episode = season.find_episode(episodeid)
        else:
            vod: Movie = self.movies.find_movie(movieid)
        return vod

    def __play_movie(self, li: xbmcgui.ListItem):
        vod = self.__get_episode_or_movie(li)
        resumePoint = self.videoHelper.get_resume_point(vod.id)
        self.stop_monitor()
        self.playingListitem = li
        self.videoHelper.play_movie(vod, resumePoint)
        self.start_monitor(vod.id)

    def __list_seasons(self):
        # pylint: disable=no-member
        movielist: xbmcgui.ControlList = self.getControl(self.MOVIELIST)
        li = movielist.getSelectedItem()
        serie: Series = self.series.find_serie(self.currentseriesId)
        listing = []
        if not serie.hasdetails:
            errors = self.series.update_season_details(serie)
            if errors:
                xbmcgui.Dialog().ok('Error',f'{errors} while processing seasons, see log for details')
        for season in serie.seasons:
            li = self.listitemHelper.listitem_from_season(season)
            listing.append(li)

        movielist.reset()
        movielist.addItems(listing)
        movielist.selectItem(0)
        self.screenstate = self.ScreenState.SEASONS

    def __list_episodes(self):
        # pylint: disable=no-member
        movielist: xbmcgui.ControlList = self.getControl(self.MOVIELIST)
        listing = []

        serie: Series = self.series.find_serie(self.currentseriesId)
        season:Season = serie.find_season(self.currentseasonId)

        if serie is None or season is None:
            xbmcgui.Dialog().ok('Error', 'Missing series/season')
            return
        errors = 0
        for episode in season.episodes:
            errors += self.series.update_episode_details(episode)
            li = self.listitemHelper.listitem_from_episode(episode)
            listing.append(li)
        if errors > 0:
            xbmcgui.Dialog().ok('Error',f'{errors} while processing episodes, see log for details')
        movielist.reset()
        movielist.addItems(listing)
        movielist.selectItem(0)
        self.screenstate = self.ScreenState.EPISODES

    def sort_listitems(self, listing: list, sortby: int, sortorder: int):
        """
        Method to sort the listitems, depending on the parameters
        
        :param self: 
        :param listing: a list with listitems
        :type listing: list
        :param sortby: the key on which to sort
        :type sortby: int
        :param sortorder: the order of sorting
        :type sortorder: int
        """
        if int(sortby) == utils.SharedProperties.TEXTID_NAME:
            if int(sortorder) == utils.SharedProperties.TEXTID_ASCENDING:
                listing.sort(key=lambda x: x.getVideoInfoTag().getTitle().lower())
            else:
                listing.sort(key=lambda x: x.getVideoInfoTag().getTitle().lower(), reverse=True)

    def __list_overview(self,categoryId):
        listingseries = []
        listingmovies = []

        dlg = xbmcgui.DialogProgress()
        dlg.create('ZiggoTV', 'Loading series...')

        # pylint: disable=no-member
        if self.series is not None:
            self.series.save()
            self.series = None
        movielistctrl: xbmcgui.ControlList = self.getControl(self.MOVIELIST)
        self.series = SeriesList(self.addon, categoryId)
        seasonerrors = 0
        for serie in self.series.series:
            if not serie.hasdetails:
                seasonerrors += self.series.update_season_details(serie)
            li = self.listitemHelper.listitem_from_series(serie)
            listingseries.append(li)

        self.series.save()

        dlg.update(50, 'Loading movies...')

        if self.movies is not None:
            self.movies.save()
            self.movies = None
        self.movies = MovieList(self.addon, categoryId)
        movieerrors = 0
        for movie in self.movies.movies:
            if not movie.hasdetails:
                movieerrors += self.movies.update_details(movie)
            li = self.listitemHelper.listitem_from_movie(movie)
            listingmovies.append(li)
        self.movies.save()

        movielistctrl.reset()
        sortby, sortorder = self.sharedproperties.get_sort_options_movies()
        self.sort_listitems(listingseries, sortby, sortorder)
        self.sort_listitems(listingmovies, sortby, sortorder)

        dlg.close()
        if seasonerrors > 0 or movieerrors > 0 or self.movies.parseerrors > 0 or self.series.parseerrors > 0:
            xbmcgui.Dialog().ok('Error','Errors while processing seasons/movies, see log for details')

        movielistctrl.addItems(listingseries)
        movielistctrl.addItems(listingmovies)
        movielistctrl.selectItem(0)
        self.screenstate = self.ScreenState.OVERVIEW

    def update_movie_details(self,li:xbmcgui.ListItem):
        """
        method to update the movie details if needed
        
        :param self: 
        :param li: listitem with the movie to be updated
        :type li: xbmcgui.ListItem
        """
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        movieid = tag.getUniqueID('ziggomovieid')
        movie = self.movies.find_movie(movieid)
        if not movie.hasdetails:
            self.movies.update_details(movie)

    def update_episode_details(self,li:xbmcgui.ListItem):
        """
        method to update the episode details if needed
        
        :param self: 
        :param li: listitem with the episode to be updated
        :type li: xbmcgui.ListItem
        """
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        episodeid = tag.getUniqueID('ziggoepisodeid')
        serie = self.series.find_serie(self.currentseriesId)
        season = serie.find_season(self.currentseasonId)
        episode = season.find_episode(episodeid)
        if not episode.hasdetails:
            self.series.update_episode_details(episode)

    def update_series_details(self,li:xbmcgui.ListItem):
        """
        method to update the series details if needed
        
        :param self: 
        :param li: listitem with the series to be updated
        :type li: xbmcgui.ListItem
        """
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        serieid = tag.getUniqueID('ziggoseriesid')
        serie = self.series.find_serie(serieid)
        if not serie.hasdetails:
            self.series.update_season_details(serie)

    def update_season_details(self,li:xbmcgui.ListItem):
        """
        method to update the season details if needed
        currently no implementation
        
        :param self: 
        :param li: listitem with the movie to be updated
        :type li: xbmcgui.ListItem
        """

    def onInit(self):
        # give kodi a bit of (processing) time to add all items to the container
        xbmc.sleep(100)
        self.__showmoviecategories()

    def onFocus(self, controlId):
        # pylint: disable=no-member
        if controlId == self.MOVIELIST:
            movielist: xbmcgui.ControlList = self.getControl(self.MOVIELIST)
            li = movielist.getSelectedItem()
            if li.getProperty('isMovie'):
                self.update_movie_details(li)
            elif li.getProperty('isEpisode'):
                self.update_episode_details(li)
            elif li.getProperty('IsSeries'):
                self.update_series_details(li)
            elif li.getProperty('IsSeason'):
                self.update_season_details(li)

        super().onFocus(controlId)

    def onAction(self, action: xbmcgui.Action):
        if action.getId() == xbmcgui.ACTION_STOP:
            xbmc.log('Window onAction STOP', xbmc.LOGDEBUG)
            self.close()
            return

        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU or action.getId() == xbmcgui.ACTION_NAV_BACK:
            xbmc.log('Window onAction PREVIOUS or BACK', xbmc.LOGDEBUG)
            if self.screenstate == self.ScreenState.SEASONS:
                self.__list_overview(self.currentcategoryId)
                return
            if self.screenstate == self.ScreenState.EPISODES:
                self.inepisodes = False
                self.__list_seasons()
                return

        super().onAction(action)

    def onClick(self, controlId):
        # pylint: disable=no-member
        if controlId == self.MOVIECATEGORIESLIST:
            categorylist: xbmcgui.ControlList = self.getControl(self.MOVIECATEGORIESLIST)
            li = categorylist.getSelectedItem()
            tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
            self.currentcategoryId = tag.getUniqueID('ziggoCategoryId')
            self.__list_overview(self.currentcategoryId)
            return

        if controlId == self.MOVIELIST:
            movielist: xbmcgui.ControlList = self.getControl(self.MOVIELIST)
            li = movielist.getSelectedItem()
            tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
            if li.getProperty('IsSeries') == 'true':
                self.inseasons = True
                self.inepisodes = False
                self.currentseriesId = tag.getUniqueID('ziggoseriesid')
                self.__list_seasons()
            elif li.getProperty('IsSeason') == 'true':
                self.inseasons = False
                self.inepisodes = True
                self.currentseasonId = tag.getUniqueID('ziggoseasonid')
                self.__list_episodes()
            else:
                if li.getProperty('AvailableAfter') is not None and li.getProperty('AvailableAfter') != '':
                    xbmcgui.Dialog().ok('Error', self.addon.getLocalizedString(S.MSG_CANNOTWATCH_YET))
                    return
                if li.getProperty('isPlayable') == 'false':
                    xbmcgui.Dialog().ok('Error', self.addon.getLocalizedString(S.MSG_CANNOTWATCH))
                    return
                self.__play_movie(li)
            return

        super().onClick(controlId)

    def cleanup(self):
        """
        Function perform cleanup of stored movies and series information
        
        :param self: 
        """
        xbmc.log('CLEANUP METHOD CALLED', xbmc.LOGDEBUG)
        self.series.cleanup()
        self.movies.cleanup()
        self.onClick(self.MOVIECATEGORIESLIST)

def load_moviewindow(addon: xbmcaddon.Addon):
    """
    function to create, populate and display the movie window
    
    :param addon: Description
    :type addon: xbmcaddon.Addon
    """
    try:
        # pylint: disable=import-outside-toplevel
        from resources.lib.utils import invoke_debugger
        invoke_debugger(False, 'vscode')
        check_service(addon)
        window = MovieWindow('movies.xml', addon.getAddonInfo('path'), defaultRes='1080i', addon=addon)
        window.doModal()
        window.stop_monitor()
        del window

    except WebException as exc:
        xbmcgui.Dialog().ok('Error', '{0}'.format(exc.response))
        xbmc.log(traceback.format_exc(), xbmc.LOGDEBUG)
    # pylint: disable=broad-exception-caught
    except Exception as exc:
        xbmcgui.Dialog().ok('Error', f'{exc}')
        xbmc.log(traceback.format_exc(), xbmc.LOGDEBUG)
