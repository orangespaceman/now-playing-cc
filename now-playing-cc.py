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
import socket

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import pychromecast
from pychromecast.controllers.media import MediaStatusListener
from pychromecast.controllers.receiver import CastStatusListener


class NowPlayingListener:
    data_fields = [
        "title",
        "artist",
        "album_name",
        "playlist",
        "release_date",
        "player_state",
    ]

    cache_dir = "./static/cache/"

    def __init__(self, name, cast):
        self.name = name
        self.cast = cast

    def handle_data(self):
        refresh_manually = False
        data = {}
        self.update_data(data, self.cast.status)
        self.update_data(data, self.cast.media_controller.status)

        if hasattr(
            self.cast.media_controller.status, "player_state"
        ) and self.cast.media_controller.status.player_state in [
            "PLAYING",
            "BUFFERING",
        ]:
            if any(
                station in ["Radio 6 Music", "BBC Radio 6 Music"]
                for station in [data["playlist"], data["title"]]
            ):
                self.check_6music_state(data)
                refresh_manually = True
            elif "FIP" in [data["title"], data["playlist"]] or (
                "Radio France" in self.cast.status.display_name
            ):
                self.check_fip_state(data)
                refresh_manually = True

        self.request_release_date(data, self.cast.media_controller.status)
        self.update_json(data)

        if refresh_manually:
            self.debug("manually refreshing", "-")
            time.sleep(60)
            self.handle_data()

    def update_data(self, data, chromecast_data):
        self.debug("Chromcast Data: ", chromecast_data)

        for data_field in self.data_fields:
            if hasattr(chromecast_data, data_field):
                data[data_field] = getattr(chromecast_data, data_field)

        if hasattr(chromecast_data, "images") and len(chromecast_data.images) > 0:
            image_url = chromecast_data.images[0].url
            file_name = "{}.jpg".format(image_url.split("/")[-1])
            data["image"] = file_name
            self.cache_image(image_url, file_name)

        if hasattr(chromecast_data, "media_custom_data") and self.has_key_deep(
            chromecast_data.media_custom_data,
            "playerPlaybackState",
            "context",
            "metadata",
            "context_description",
        ):
            data["playlist"] = chromecast_data.media_custom_data["playerPlaybackState"][
                "context"
            ]["metadata"]["context_description"]
        else:
            data["playlist"] = None

    def request_release_date(self, data, chromecast_data):
        if data["title"] == "" or data["artist"] == "" or data["album_name"] == "":
            return

        if (
            hasattr(chromecast_data, "content_id")
            and chromecast_data.content_id
            and "spotify:track:" in chromecast_data.content_id
        ):
            try:
                sp = spotipy.Spotify(
                    auth_manager=SpotifyClientCredentials(
                        client_id=config.SPOTIFY_CLIENT_ID,
                        client_secret=config.SPOTIFY_CLIENT_SECRET,
                    )
                )

                track = sp.track(chromecast_data.content_id)
                if self.has_key_deep(track, "album", "release_date"):
                    try:
                        date_string = track["album"]["release_date"]
                        date_precision = track["album"]["release_date_precision"]
                        if date_precision == "year":
                            data["release_date"] = date_string
                        elif date_precision == "month":
                            date_obj = datetime.datetime.strptime(date_string, "%Y-%m")
                            data["release_date"] = date_obj.strftime("%B %Y")
                        else:
                            date_obj = datetime.datetime.strptime(
                                date_string, "%Y-%m-%d"
                            )
                            data["release_date"] = date_obj.strftime("%-d %B %Y")
                    except Exception as e:
                        self.debug("Date exception", e)
            except Exception as e:
                self.debug("Spotify API exception", e)

    def check_6music_state(self, data):
        self.debug("checking 6music state!", "-")

        current_track = self.request_6music_data()

        if (
            current_track is None
            or "error" in current_track
            or "data" not in current_track
        ):
            self.debug("no current 6music track!", "-")
            return

        image_url = current_track["data"][0]["image_url"].replace("{recipe}", "640x640")
        file_name = "{}.jpg".format(image_url.split("/")[-1])
        data["image"] = file_name
        self.cache_image(image_url, file_name)

        data["playlist"] = data["title"]
        data["album_name"] = ""
        data["artist"] = current_track["data"][0]["titles"]["primary"]
        data["title"] = current_track["data"][0]["titles"]["secondary"]

    def request_6music_data(self):
        request = (
            "https://rms.api.bbc.co.uk/v2/services/bbc_6music/segments/latest?limit=1"
        )
        try:
            response = requests.get(request)
            self.debug("6music response", response.json())
            return response.json()
        except requests.exceptions.RequestException as e:
            self.debug("Requests exception", e)

    def check_fip_state(self, data):
        self.debug("checking fip state!", "-")

        current_track = self.request_fip_data()

        if (
            current_track is None
            or "error" in current_track
            or "now" not in current_track
        ):
            self.debug("no current fip track!", "-")
            return

        image_url = current_track["now"]["visuals"]["card"]["src"]
        file_name = "{}.jpg".format(image_url.split("/")[-1])
        data["image"] = file_name
        self.cache_image(image_url, file_name)

        data["playlist"] = data["title"]
        data["album_name"] = current_track["now"]["song"]["release"]["title"]
        data["release_date"] = current_track["now"]["song"]["year"]
        data["artist"] = current_track["now"]["secondLine"]["title"]
        data["title"] = current_track["now"]["firstLine"]["title"]

    def request_fip_data(self):
        request = "https://www.radiofrance.fr/fip/api/live"
        try:
            response = requests.get(request)
            self.debug("Fip response", response.json())
            return response.json()
        except requests.exceptions.RequestException as e:
            self.debug("Requests exception", e)

    def cache_image(self, url, file_name):
        file_path = "{}{}".format(self.cache_dir, file_name)
        if os.path.isfile(file_path):
            return

        self.debug("caching image", file_name)

        response = requests.get(url, stream=True)
        with open("{}{}".format(self.cache_dir, file_name), "wb") as out_file:
            shutil.copyfileobj(response.raw, out_file)
        del response

    def update_json(self, data):
        data["last_updated"] = str(datetime.datetime.now()).split(".")[0]
        data["ip"] = self.get_ip()
        with open("./static/data.json", "w") as outfile:
            json.dump(data, outfile, ensure_ascii=False, indent=4, sort_keys=True)
        self.debug("JSON file updated", data)

    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            s.connect(("10.254.254.254", 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = "127.0.0.1"
        finally:
            s.close()
        return IP

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
        try:
            self.handle_data()
        except Exception as e:
            self.debug("Exception in media status callback", e)

    def load_media_failed(self, item, error_code):
        try:
            self.handle_data()
        except Exception as e:
            self.debug("Exception in media load failure", e)


class NowPlayingCC:
    def __init__(self):
        self.init_chromecast()

    def init_chromecast(self):
        chromecasts, browser = pychromecast.get_listed_chromecasts(
            friendly_names=[config.CHROMECAST],
        )

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
