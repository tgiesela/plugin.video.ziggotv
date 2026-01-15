# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

import json
from pathlib import Path
import threading
import unittest

from resources.lib.globals import G
from resources.lib.movies import Episode, MovieList, SeriesList
from resources.lib.proxyserver import ProxyServer
from resources.lib.utils import ProxyHelper
from resources.lib.webcalls import LoginSession
from tests.test_base import TestBase

class InvalidAgeError(Exception):
    def __init__(self, msg="Age must be between 0 and 120"):
        self.msg = msg
        super().__init__(self.msg)

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
        self.addon.setSettingBool('print-response-content', False)
        self.addon.setSettingBool('print-request-content', False)
        self.do_login()
        self.logon_via_proxy()
        moviesDetails = json.loads(Path(G.MOVIE_INFO).read_text(encoding='utf-8'))
        moviesDetails = []
        Path(G.MOVIE_INFO).write_text(json.dumps(moviesDetails), encoding='utf-8')
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
            series.save()
            movies = MovieList(self.addon, screen['id'])
            for movie in movies.movies:
                if not movie.hasdetails:
                    movies.update_details(movie)
                print(f'Movie: {movie.id}, title: {movie.asset.title}')
            movies.save()

if __name__ == '__main__':
    unittest.main()
