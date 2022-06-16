try:
    import config
except Exception:
    print("You must create a config.py file")
    import sys
    sys.exit(0)

import sys
import datetime
import itertools
import json
import os
import shutil
import time
import requests

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import pychromecast
from pychromecast.controllers.media import MediaStatusListener
from pychromecast.controllers.receiver import CastStatusListener


class NowPlayingListener():
    data_fields = [
        'title',
        'artist',
        'album_name',
        'playlist',
        'release_date',
        'player_state',
    ]

    cache_dir = "./static/cache/"

    def __init__(self, name, cast):
        self.name = name
        self.cast = cast
        self.init_last_fm_api_keys()

    def handle_data(self):
        data = {}
        self.update_data(data, self.cast.status)
        self.update_data(data, self.cast.media_controller.status)
        if (hasattr(self.cast.media_controller.status, 'player_state')
                and self.cast.media_controller.status.player_state == 'PLAYING'):
            self.check_6music_state(data)
        self.request_release_date(data, self.cast.media_controller.status)
        self.update_json(data)

        if 'Radio 6 Music' in data['title']:
            time.sleep(30)
            self.handle_data()

    def update_data(self, data, chromecast_data):
        self.debug('Chromcast Data: ', chromecast_data)

        for data_field in self.data_fields:
            if hasattr(chromecast_data, data_field):
                data[data_field] = getattr(chromecast_data, data_field)

        if hasattr(chromecast_data, 'images') and len(chromecast_data.images) > 0:
            image_url = chromecast_data.images[0].url
            file_name = "{}.jpg".format(image_url.split('/')[-1])
            data['image'] = file_name
            self.cache_image(image_url, file_name)

        if (hasattr(chromecast_data, 'media_custom_data')
                and self.has_key_deep(chromecast_data.media_custom_data, 'playerPlaybackState', 'context', 'metadata',
                                      'context_description')):
            data['playlist'] = (
                chromecast_data.media_custom_data['playerPlaybackState']['context']['metadata']['context_description'])
        else:
            data['playlist'] = None

    def init_last_fm_api_keys(self):
        self.last_fm_api_keys = (itertools.cycle(config.LAST_FM_API_KEYS))

    def check_6music_state(self, data):
        if 'Radio 6 Music' not in data['title']:
            return

        current_track = self.request_data_from_lastfm('track')

        if current_track is None or 'error' in current_track or 'recenttracks' not in current_track:
            return

        data['playlist'] = data['title']
        data['album_name'] = current_track['recenttracks']['track'][0]['album']['#text']
        data['artist'] = current_track['recenttracks']['track'][0]['artist']['#text']
        data['title'] = current_track['recenttracks']['track'][0]['name']

    def request_release_date(self, data, chromecast_data):
        if data['title'] == '' or data['artist'] == '' or data['album_name'] == '':
            return

        if hasattr(chromecast_data, 'content_id') and 'spotify:track:' in chromecast_data.content_id:
            sp = spotipy.Spotify(
                auth_manager=SpotifyClientCredentials(
                    client_id=config.SPOTIFY_CLIENT_ID,
                    client_secret=config.SPOTIFY_CLIENT_SECRET,
                ))

            track = sp.track(chromecast_data.content_id)
            if self.has_key_deep(track, 'album', 'release_date'):
                try:
                    date_string = track['album']['release_date']
                    date_precision = track['album']['release_date_precision']
                    if date_precision == 'year':
                        data['release_date'] = date_string
                    elif date_precision == 'month':
                        date_obj = datetime.datetime.strptime(date_string, '%Y-%m')
                        data['release_date'] = date_obj.strftime("%B %Y")
                    else:
                        date_obj = datetime.datetime.strptime(date_string, '%Y-%m-%d')
                        data['release_date'] = date_obj.strftime("%-d %B %Y")
                except Exception as e:
                    self.debug("Date exception", e)

    def request_data_from_lastfm(self, required_data, param=None):
        api_key = next(self.last_fm_api_keys)
        if required_data == 'track':
            method = 'user.getRecentTracks'
            data = 'user=bbc6music'
        elif required_data == 'album':
            method = 'album.getInfo'
            data = param
        elif required_data == 'image':
            method = 'artist.getInfo'
            data = "mbid={}".format(param)
        request = "https://ws.audioscrobbler.com/2.0/?method={}&{}&api_key={}&limit=1&format=json".format(
            method, data, api_key)
        self.debug("Last FM {} Request".format(required_data), request)
        try:
            response = requests.get(request)
            self.debug("Last FM {} Response".format(required_data), response.json())
            return response.json()
        except requests.exceptions.RequestException as e:
            self.debug("Requests exception", e)

    def cache_image(self, url, file_name):
        file_path = "{}{}".format(self.cache_dir, file_name)
        if os.path.isfile(file_path):
            return

        self.debug('caching image', file_name)

        response = requests.get(url, stream=True)
        with open("{}{}".format(self.cache_dir, file_name), 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        del response

    def update_json(self, data):
        data['last_updated'] = str(datetime.datetime.now()).split(".")[0]
        with open('./static/data.json', 'w') as outfile:
            json.dump(data, outfile, ensure_ascii=False, indent=4, sort_keys=True)
        self.debug('JSON file updated', data)

    def has_key_deep(self, dict, *names):
        for name in names:
            if name not in dict:
                return False
            dict = dict[name]
        return True

    def debug(self, title, message):
        if config.DEBUG:
            print("{}:\n{}".format(title, message))
            print("\n-------\n")


class MyCastStatusListener(CastStatusListener, NowPlayingListener):
    def new_cast_status(self, status):
        self.handle_data()


class MyMediaStatusListener(MediaStatusListener, NowPlayingListener):
    def new_media_status(self, status):
        self.handle_data()

    def load_media_failed(self, item, error_code):
        self.handle_data()


class NowPlayingCC:
    def __init__(self):
        self.init_chromecast()

    def init_chromecast(self):
        chromecasts, browser = pychromecast.get_listed_chromecasts(friendly_names=[config.CHROMECAST], )

        if not chromecasts:
            print(f'No chromecast with name "{config.CHROMECAST}" discovered')
            sys.exit(1)

        chromecast = chromecasts[0]
        chromecast.wait()

        print(f'Found chromecast with name "{config.CHROMECAST}"')

        listenerCast = MyCastStatusListener(chromecast.name, chromecast)
        chromecast.register_status_listener(listenerCast)

        listenerMedia = MyMediaStatusListener(chromecast.name, chromecast)
        chromecast.media_controller.register_status_listener(listenerMedia)

        browser.stop_discovery()

        while True:
            pass


np = NowPlayingCC()
