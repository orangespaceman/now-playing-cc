# Now Playing - Chromecast

Display in a web page details of the current Spotify/BBC 6music track that's playing on a Chromecast / Google Home on the same local network.


## Setup

Clone this repo, e.g. onto a raspberry pi.


Create a virtualenv:
```
virtualenv env --python=/path/to/python3
```

Activate virtualenv:

```
source env/bin/activate
```

Install requirements:

```
pip install -r requirements.txt
```

Duplicate the `config.example.py` file, call it `config.py`, and add the name of the name of your Chromecast, plus last.fm API key(s) which are used to get the latest BBC 6music track and artwork.

Start chromecast listener
```
python now-playing-cc.py
```

Start web server
```
FLASK_APP=serve.py flask run --host=0.0.0.0
```

The previous two commands could be created as services to start automatically when a Pi turns on:

```
sudo cp now-playing-cc.service /lib/systemd/system/
sudo cp serve.service /lib/systemd/system/
sudo systemctl enable now-playing-cc.service
sudo systemctl enable serve.service
```

To manually start/stop these services, run:

```
sudo service now-playing-cc start
sudo service now-playing-cc stop
sudo service now-playing-cc status
(etc)
```

Open http://localhost:5000 in a web browser to see it!
