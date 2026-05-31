# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

import json
from pathlib import Path

from resources.lib.globals import G
from resources.lib.movies import Episode, MovieList, SeriesList

class InvalidAgeError(Exception):
    def __init__(self, msg="Age must be between 0 and 120"):
        self.msg = msg
        super().__init__(self.msg)

class TestMovies:

    def test_series(self, activewebsession):
        activewebsession.addon.setSettingBool('print-response-content', False)
        activewebsession.addon.setSettingBool('print-request-content', False)
        moviesDetails = []
        Path(G.MOVIE_INFO).write_text(json.dumps(moviesDetails), encoding='utf-8')
        response = activewebsession.session.obtain_vod_screens()
        combinedlist = response['screens']
        combinedlist.append(response['hotlinks']['adultRentScreen'])

        for screen in combinedlist:
            print('Screen: ' + screen['title'], 'id: ', screen['id'])
            series = SeriesList(activewebsession.addon, screen['id'])
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
            movies = MovieList(activewebsession.addon, screen['id'])
            for movie in movies.movies:
                if not movie.hasdetails:
                    movies.update_details(movie)
                print(f'Movie: {movie.id}, title: {movie.asset.title}')
            movies.save()

# if __name__ == '__main__':
#     unittest.main()
