# ProbeDesign
Design primers to use with Roche's fluorescent probe libraries

Check it out at [primers.neoformit.com](http://primers.neoformit.com/)


Development setup
------

> Tested on Linux Ubuntu 20.04 with Python 3.8 runtime

> Recommend installing in virtual environment

Clone the repo to home directory and install dependancies:

```bash
git clone https://github.com/pluckthechicken/primerdesign.git
cd primerdesign
pip install requirements.txt
python manage.py migrate
./setup.sh
```

Run development server (`--insecure` allows local static file serving)

`python manage.py runserver --insecure`


Production deployment
------

This is a little more complex due to setting up a webserver.

No need to do anything "fancy" in the server config as it's a single-page app with short request times.

I'm currently running this with Nginx reverse-proxying for Gunicorn (see `gunicorn.py`).

One day I might get around to making a `setup.py` here for easy install/deploy
