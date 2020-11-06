# ProbeDesign
Design primers to use with Roche's fluorescent probe libraries

Check out a running example at [primers.neoformit.com](http://primers.neoformit.com/)


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

This get a little more complex due to setting up the webserver etc.

I'm currently running this with Nginx reverse-proxying for Gunicorn.

It doesn't need anything special in the server config as it's a single-page app with short request times.
