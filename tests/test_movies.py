# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

import json
import threading
import unittest

from resources.lib.movies import Episode, MovieList, SeriesList
from resources.lib.proxyserver import ProxyServer
from resources.lib.utils import ProxyHelper
from resources.lib.webcalls import LoginSession
from tests.test_base import TestBase

class TestMovies(TestBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proxyServer: ProxyServer = None
        self.thread: threading.Thread = None
        self.helper = ProxyHelper(self.addon)

    def logon_via_proxy(self):
        with open('c:/temp/credentials.json', 'r', encoding='utf-8') as credfile:
            credentials = json.loads(credfile.read())
        rslt = self.helper.dynamic_call(LoginSession.login, username=credentials['username'],
                                        password=credentials['password'])
        print(rslt)

    def test_series(self):
        self.do_login()
        self.addon.setSetting('print-response-content', 'false')
        self.addon.setSetting('print-request-content', 'false')
        self.logon_via_proxy()

        response = self.session.obtain_vod_screens()
        combinedlist = response['screens']
        combinedlist.append(response['hotlinks']['adultRentScreen'])
        for screen in combinedlist:
            print('Screen: ' + screen['title'], 'id: ', screen['id'])
            series = SeriesList(self.addon, screen['id'])
            for serie in series.series:
                if not serie.hasdetails:
                    series.update_season_details(serie)
                for season in serie.seasons:
                    episode:Episode
                    for episode in season.episodes:
                        if not episode.hasdetails:
                            series.update_episode_details(episode)
                        if episode.isEvent():
                            event = series.get_event(episode)
                            print(event.id)
                print(f'Serie: {serie.id}, title: {serie.title}')
            movies = MovieList(self.addon, screen['id'])
            for movie in movies.movies:
                if not movie.hasdetails:
                    movies.update_details(movie)
                print(f'Movie: {movie.id}, title: {movie.asset.title}')
            # screenDetails = self.session.obtain_vod_screen_details(screen['id'])
            # if 'collections' in screenDetails:
            #     for collection in screenDetails['collections']:
            #         self.process_collection_movies(collection)

if __name__ == '__main__':
    unittest.main()
