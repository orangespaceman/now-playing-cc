try:
    import config
except Exception:
    print("You must create a config.py file")
    import sys
    sys.exit(0)

import datetime
import itertools
import json
import os
import shutil
import time
import requests

import pychromecast
from pychromecast.controllers.media import MediaStatusListener
from pychromecast.controllers.receiver import CastStatusListener


class NowPlayingListener():
    data_fields = [
        'title',
        'artist',
        'album_name',
        'player_state',
    ]

    cache_dir = "./static/cache/"

    last_fm_previous_track = None
    last_fm_previous_artist_mbid = None
    last_fm_previous_artist_image = None
    loop_counter = 0

    def __init__(self, name, cast):
        self.name = name
        self.cast = cast
        self.init_last_fm_api_keys()

    def handle_data(self):
        data = {}
        self.update_data(data, self.cast.status)
        self.update_data(data, self.cast.media_controller.status)
        self.check_lastfm_state(data)
        self.update_json(data)

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

    def init_last_fm_api_keys(self):
        self.last_fm_api_keys = (itertools.cycle(config.LAST_FM_API_KEYS))

    def check_lastfm_state(self, data):
        if data['title'] != 'Radio 6 Music' and data['title'] != 'BBC Radio 6 Music':
            return

        if self.loop_counter % 4 != 0:
            current_track = self.last_fm_previous_track
        else:
            current_track = self.request_data_from_lastfm('track')
            self.last_fm_previous_track = current_track

        if current_track is None or 'error' in current_track or 'recenttracks' not in current_track:
            return

        artist = current_track['recenttracks']['track'][0]['artist']

        data['album_name'] = data['title']
        data['artist'] = artist['#text']
        data['title'] = current_track['recenttracks']['track'][0]['name']

        if not artist["mbid"]:
            self.debug("Last FM image", "No mbid supplied")
            return

        if self.last_fm_previous_artist_mbid == artist["mbid"]:
            data['image'] = self.last_fm_previous_artist_image
            self.debug("Last FM image", "mbid is same as last artist")
            return

        self.last_fm_previous_artist_mbid = artist["mbid"]

        image = self.request_data_from_lastfm('image', artist["mbid"])
        if 'error' in image or 'artist' not in image or len(image["artist"]["image"]) == 0:
            self.debug("Last FM image", image)
            return

        image_url = image["artist"]["image"][len(image["artist"]["image"]) - 1]["#text"]
        if len(image_url) == 0:
            self.debug("Last FM image", "image url empty")
            return

        file_name = "{}".format(image_url.split('/')[-1])
        data['image'] = file_name
        self.cache_image(image_url, file_name)
        self.last_fm_previous_artist_image = data['image']

    def request_data_from_lastfm(self, required_data, param=None):
        api_key = next(self.last_fm_api_keys)
        if required_data == 'track':
            method = 'user.getRecentTracks'
            data = 'user=bbc6music'
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

    def debug(self, title, message):
        if config.DEBUG:
            print("{}:\n{}".format(title, message))
            print("\n-------\n")


class MyCastStatusListener(CastStatusListener, NowPlayingListener):
    def new_cast_status(self, status):
        self.debug("[", time.ctime(), " - ", self.name, "] status chromecast change:")
        self.debug(status)
        self.handle_data()


class MyMediaStatusListener(MediaStatusListener, NowPlayingListener):
    def new_media_status(self, status):
        self.debug("[", time.ctime(), " - ", self.name, "] status media change:")
        self.debug(status)
        self.handle_data()

    def load_media_failed(self, item, error_code):
        self.debug("[", time.ctime(), " - ", self.name, item, error_code, "] load media failed:")
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
