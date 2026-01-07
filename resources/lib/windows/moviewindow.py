from enum import IntEnum
import os
import json
from pathlib import Path
import threading
import time
import traceback
import typing
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

from resources.lib import utils
from resources.lib.channel import Channel
from resources.lib.globals import G, S
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.utils import ProxyHelper, WebException, check_service
from resources.lib.videohelpers import VideoHelpers
from resources.lib.webcalls import LoginSession
from resources.lib.windows.basewindow import baseWindow
class movieWindow(baseWindow):
    CHANNELBUTTON=5
    EPGBUTTON=6
    RECORDINGSBUTTON=7
    MOVIESBUTTON=8
    MOVIECATEGORIESLIST=150
    RECENTRECORDINGSLIST=250
    MOVIELIST=50
    class screenState(IntEnum):
        CATEGORY = 1,
        OVERVIEW = 2,
        SEASONS = 3,
        EPISODES = 4

    def __init__(self, xmlFilename, scriptPath, defaultSkin = "Default", defaultRes = "720p", isMedia = False, addon=''):
        super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes, isMedia, addon)
        self.ADDON = addon
        self.movieList = None
        self.helper = ProxyHelper(self.ADDON)
        self.screens = None
        self.listitemHelper = ListitemHelper(self.ADDON)
        self.videoHelper = VideoHelpers(self.ADDON)
        self.movieOverviews = []
        self.seriesOverviews = []
        self.ADDONPATH = xbmcvfs.translatePath(self.ADDON.getAddonInfo('profile'))
        self.screenstate = self.screenState.CATEGORY
        self.currentcategoryId = None
        self.currentseasonId = None
        self.currentseriesId = None
        self.thread = None

    def __del__(self):
        self.keyboardmonitor = None

    def __plugin_path(self, name):
        """
        Function returns the full filename of the userdata folder of the addon
        @param name:
        @return:
        """
        return self.ADDONPATH + name

    def __showmoviecategories(self):
        listing = []
        # this puts the focus on the first button of the screen
        moviecategorieslist: xbmcgui.ControlList = self.getControl(self.MOVIECATEGORIESLIST)

        response = self.helper.dynamic_call(LoginSession.obtain_vod_screens)
        self.screens = response['screens']
#       logos in screen['brandLogoImage','logoNonfocused']

        if self.ADDON.getSettingBool('adult-allowed'):
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

            if 'brandLogoImage' in screen['theme']:
                iconurl = screen['theme']['brandLogoImage']
            elif 'logoNonfocused' in screen['theme']:
                iconurl = screen['theme']['logoNonfocused']
            elif 'background' in screen['theme']:
                iconurl = screen['theme']['background']
            else:
                iconurl = ''
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
    
    def __load_movie_overviews(self):
        """
        loads the movies from disk if the file is present and stores it in the class variable movieOverviews
        this is used in between calls from the addon
        @return: nothing
        """
        file = self.__plugin_path(G.MOVIE_INFO)
        if Path(file).exists():
            self.movieOverviews = json.loads(Path(file).read_text(encoding='utf-8'))
        else:
            self.movieOverviews = []

    def __load_series_overviews(self):
        """
        loads the series from disk if the file is present and stores it in the class variable seriesOverviews
        @return: nothing
        """
        file = self.__plugin_path(G.SERIES_INFO)
        if Path(file).exists():
            self.seriesOverviews = json.loads(Path(file).read_text(encoding='utf-8'))
        else:
            self.seriesOverviews = []

    def __save_movie_overviews(self):
        """
        Saves the obtained movies in a disk file to be used during subsequent calls to the addon
        @return:
        """
        Path(self.__plugin_path(G.MOVIE_INFO)).write_text(json.dumps(self.movieOverviews), encoding='utf-8')

    def __save_series_overviews(self):
        """
        Saves the obtained series in a disk file to be used during subsequent calls to the addon
        @return:
        """
        Path(self.__plugin_path(G.SERIES_INFO)).write_text(json.dumps(self.seriesOverviews), encoding='utf-8')

    def __get_series_details(self, itemId):
        for overview in self.seriesOverviews:
            if overview['id'] == itemId:
                return overview

        overview = self.helper.dynamic_call(LoginSession.obtain_series_overview, seriesId=itemId)
        self.seriesOverviews.append(overview)
        return overview

    def __update_asset_details(self, item):
        self.movieOverviews.remove(item)
        if 'brandingProviderId' in item:
            overview = self.helper.dynamic_call(LoginSession.obtain_asset_details, assetId=item['id'],
                                                brandingProviderId=item['brandingProviderId'])
        else:
            overview = self.helper.dynamic_call(LoginSession.obtain_asset_details, assetId=item['id'])
        self.movieOverviews.append(overview)

    def __get_asset_details(self,item):
        for overview in self.movieOverviews:
            if overview['id'] == item['id']:
                return overview

        if 'brandingProviderId' in item:
            overview = self.helper.dynamic_call(LoginSession.obtain_asset_details, assetId=item['id'],
                                                brandingProviderId=item['brandingProviderId'])
        else:
            overview = self.helper.dynamic_call(LoginSession.obtain_asset_details, assetId=item['id'])
        self.movieOverviews.append(overview)
        return overview

    def __get_playable_instance(self,overview):
        if 'instances' in overview:
            for instance in overview['instances']:
                if instance['goPlayable']:
                    return instance

            return overview['instances'][0]  # return the first one if none was goPlayable
        return None

    def start_monitor(self, movie):
        self.thread = threading.Thread(target=self.videoHelper.monitor_state,args=(movie['id'],))
        self.thread.start()
    
    def stop_monitor(self):
        if self.thread is not None:
            self.videoHelper.stop_player()
            self.thread.join()
            self.thread = None
   
    def __play_movie(self, li: xbmcgui.ListItem):
        self.__load_movie_overviews()
        _overview = None
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        movieid = tag.getUniqueID('ziggomovieid')
        instanceid = tag.getUniqueID('ziggoinstanceid')
        offerid = tag.getUniqueID('ziggoofferid')
        for overview in self.movieOverviews:
            if overview['id'] == movieid:
                _overview = overview
        if _overview is None:
            raise RuntimeError('MovieId no longer found!!')

        for instance in _overview['instances']:
            if instance['id'] == instanceid:
                _instance = instance
                break

        if _instance is None:
            raise RuntimeError('Instance not found in episode overviews!!')

        for offer in _instance['offers']:
            if offer['id'] == offerid:
                _offer = offer
                break
           
        if _offer is None:
            raise RuntimeError('Offer not found in episode overviews instances!!')

        self.videoHelper = VideoHelpers(self.ADDON)
        resumePoint = self.videoHelper.get_resume_point(movieid)
        self.stop_monitor()
        self.videoHelper.play_movie(_overview, resumePoint, _instance, _offer)
        self.start_monitor(_overview)

    def __list_seasons(self, seriesId: str):
        movielist: xbmcgui.ControlList = self.getControl(self.MOVIELIST)
        li = movielist.getSelectedItem()

        listing = []
        self.__load_series_overviews()
        serie_overview = self.__get_series_details(seriesId)
        if not 'seasons' in serie_overview:
            seasons = self.helper.dynamic_call(LoginSession.get_episode_list, item=seriesId)
            if seasons is not None:
                serie_overview.update({'seasons': seasons['seasons']})
            else:
                raise RuntimeError('Cannor obtain seasons/episodes!!')

        seasons = serie_overview['seasons']
        
        for season in seasons:
            li = self.listitemHelper.listitem_from_season(season, serie_overview)
            listing.append(li)

        self.__save_series_overviews()
        movielist.reset()
        movielist.addItems(listing)
        movielist.selectItem(0)
        self.screenstate = self.screenState.SEASONS

    def __list_episodes(self, seasonId: str):
        movielist: xbmcgui.ControlList = self.getControl(self.MOVIELIST)
        listing = []
        self.__load_series_overviews()
        self.__load_movie_overviews()
        _serie = None
        _season = None
        for serie in self.seriesOverviews:
            if serie['id'] == self.currentseriesId:
                _serie = serie
                for season in serie['seasons']:
                    if season['id'] == seasonId:
                        _season = season
                        break
                break
        if _serie is None or _season is None:
            xbmcgui.Dialog().ok('Error', 'Missing series/season')
            return

        for episode in _season['episodes']:
            details = self.__get_asset_details(episode)
            episode.update({'overview': details})
            playableInstance = self.__get_playable_instance(details)
            li = self.listitemHelper.listitem_from_episode(episode, _season, details, playableInstance)
            listing.append(li)

        self.__save_series_overviews()
        self.__save_movie_overviews()
        movielist.reset()
        movielist.addItems(listing)
        movielist.selectItem(0)
        self.screenstate = self.screenState.EPISODES

    def __list_overview(self,categoryId):
        def process_items(items):
            for item in items:
                if item['id'] in itemsSeen:
                    itemid = item['id']
                    continue
                if item['type'] == 'ASSET':
                    details = self.__get_asset_details(item)
                    playableInstance = self.__get_playable_instance(details)
                    if playableInstance is not None:
                        li = self.listitemHelper.listitem_from_movie(item, details, playableInstance)
                        itemsSeen.append(item['id'])
                        listing.append(li)
                elif item['type'] == 'SERIES':
                    overview = self.__get_series_details(item['id'])
                    li = self.listitemHelper.listitem_from_movieoverview(item, overview)
                    itemsSeen.append(item['id'])
                    listing.append(li)
                else:
                    xbmc.log('Ignoring {0} with id {1}'.format(item['type'], item['id']), xbmc.LOGDEBUG)

        listing = []
        itemsSeen = []
        movielistctrl: xbmcgui.ControlList = self.getControl(self.MOVIELIST)
        self.__load_movie_overviews()
        self.__load_series_overviews()
        self.movieList = self.helper.dynamic_call(LoginSession.obtain_vod_screen_details, collectionId=categoryId)
        if 'collections' in self.movieList:
            # Note: There are multiple collections, so we can expect duplicates. Collections can be for example:
            #       Editorial, PromoTiles, Muziek, Alles
            #       We don't group like that an simply show all items presented
            for collection in self.movieList['collections']:
                process_items(collection['items'])
        self.__save_series_overviews()
        self.__save_movie_overviews()
        movielistctrl.reset()
        movielistctrl.addItems(listing)
        movielistctrl.selectItem(0)
        self.screenstate = self.screenState.OVERVIEW

    def update_movie_details(self,li:xbmcgui.ListItem):
        self.__load_movie_overviews()
        _overview = None
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        movieid = tag.getUniqueID('ziggomovieid')
        for overview in self.movieOverviews:
            if overview['id'] == movieid:
                self.__update_asset_details(overview)
                break
        self.__save_movie_overviews()

    def update_series_details(self,li:xbmcgui.ListItem):
        pass

    def update_season_details(self,li:xbmcgui.ListItem):
        pass

    def onInit(self):
        # give kodi a bit of (processing) time to add all items to the container
        xbmc.sleep(100)
        self.__showmoviecategories()
        # self.__showrecentrecordings()

    def onFocus(self, controlId):
        if controlId == self.MOVIELIST:
            list: xbmcgui.ControlList = self.getControl(self.MOVIELIST)
            li = list.getSelectedItem()
            tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
            if li.getProperty('ismovie'):
                self.update_movie_details(li)
            elif li.getProperty('IsSeries'):
                self.update_series_details(li)
            elif li.getProperty('IsSeason'):
                self.update_season_details(li)

        super().onFocus(controlId)
    
    def onAction(self, action: xbmcgui.Action):
        if action.getId() == xbmcgui.ACTION_STOP:
            xbmc.log(f'Window onAction STOP', xbmc.LOGDEBUG)
            self.close()
            return

        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU or action.getId() == xbmcgui.ACTION_NAV_BACK:
            xbmc.log(f'Window onAction PREVIOUS or BACK', xbmc.LOGDEBUG)
            if self.screenstate == self.screenState.SEASONS:
                self.__list_overview(self.currentcategoryId)
                return
            if self.screenstate == self.screenState.EPISODES:
                self.inepisodes = False
                self.__list_seasons(self.currentseriesId)
                return 

        super().onAction(action)

    def onClick(self, controlId):
        if controlId == self.MOVIECATEGORIESLIST:
            list: xbmcgui.ControlList = self.getControl(self.MOVIECATEGORIESLIST)
            li = list.getSelectedItem()
            tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
            self.currentcategoryId = tag.getUniqueID('ziggoCategoryId')
            self.__list_overview(self.currentcategoryId)
            return
        
        if controlId == self.MOVIELIST:
            list: xbmcgui.ControlList = self.getControl(self.MOVIELIST)
            li = list.getSelectedItem()
            tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
            if li.getProperty('IsSeries') == 'true':
                self.inseasons = True
                self.inepisodes = False
                self.currentseriesId = tag.getUniqueID('ziggoseriesid')
                self.__list_seasons(self.currentseriesId)
            elif li.getProperty('IsSeason') == 'true':
                self.inseasons = False
                self.inepisodes = True
                self.currentseasonId = tag.getUniqueID('ziggoseasonid')
                self.__list_episodes(self.currentseasonId)
            else:
                if li.getProperty('isPlayable') == 'false':
                    xbmcgui.Dialog().ok('Error', self.ADDON.getLocalizedString(S.MSG_CANNOTWATCH))
                    return
                self.__play_movie(li)
            return

        super().onClick(controlId)

def loadmovieWindow(addon: xbmcaddon.Addon):
    try:
        from resources.lib.utils import invoke_debugger
        invoke_debugger(True, 'vscode')
        check_service(addon)
        window = movieWindow('movies.xml', addon.getAddonInfo('path'), defaultRes='1080i', addon=addon)
        window.doModal()

    except WebException as exc:
        xbmcgui.Dialog().ok('Error', '{0}'.format(exc.response))
        xbmc.log(traceback.format_exc(), xbmc.LOGDEBUG)
    # pylint: disable=broad-exception-caught
    except Exception as exc:
        xbmcgui.Dialog().ok('Error', f'{exc}')
        xbmc.log(traceback.format_exc(), xbmc.LOGDEBUG)
