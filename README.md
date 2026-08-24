# Dumis

[![UnitTests](https://github.com/destrosvet/dumis/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/destrosvet/dumis/actions/workflows/unit-tests.yml)

Information system for homeowners' associations (SVJ). :house_with_garden:

> [!IMPORTANT]
> **Dumis is based on [SVJIS](https://github.com/svjis/svjis2)**, and is not a light customization: the visual design and a good part of the functional base have been reworked and extended. On top of everything SVJIS already provides, Dumis adds:
> - a **cadastre extract (PDF) importer** that reads a "Výpis z katastru nemovitostí", proposes building units and owners for review, and checks that each unit's ownership shares add up to 1/1 before anything is created
> - a small **admin REST API** for creating units, owners and unit/owner assignments, the first step of an API-first admin
> - a **React-based homepage**, served from the same REST API, replacing the old server-rendered boxes
> - a redesigned admin UI built around a shared sortable/dropdown list component
> - a generic **custom fields** system for attaching arbitrary data to users, units, adverts, board members, entrances and fault reports
> - server-side resizing of uploaded images so pages stay responsive instead of shipping full-resolution originals
> - a number of smaller UX fixes throughout
>
> If you're looking for the original, unmodified project, see [svjis/svjis2](https://github.com/svjis/svjis2).

## Project Description

Dumis is a CMS for Homeowners' Associations. It gives an SVJ a single place to publish news, run polls, track building faults, list classifieds, plan projects and keep an accurate record of who owns and lives in which unit - available in 9 languages out of the box.

## Features

### :newspaper: Articles & News
- Articles organized under a configurable, nestable menu, each with a cover image and file attachments
- Threaded discussions under articles (comments are editable for a configurable grace period)
- A separate News feed, a "top articles" ranking, and a Useful links list
- Polls with voting, live results and an open/closed voting window
- The public homepage is a React app fed by a REST API, assembling all of the above

### :wrench: Fault reporting
- Residents report building issues with a description, photos/attachments and comments
- Board members/resolvers manage the queue: take, close or reopen a ticket
- Full activity log per ticket, watch/subscribe for update notifications

### :moneybag: Adverts
- A classifieds board for residents, with a cover image and attachments per advert

### :clipboard: Projects
- Task/project tracking with both a list view and a Kanban board
- Configurable statuses, tags, comments, file attachments and a per-project activity log
- Watch/subscribe to a project to follow its progress

### :house_with_garden: Building & Owners (Administration)
- Building, entrances, unit types and units, each with its co-ownership share of the building (numerator/denominator)
- Owner/tenant assignment per unit, including each owner's individual share of that unit
- **Cadastre extract (PDF) import**: upload a "Výpis z katastru nemovitostí" and Dumis parses it into a proposed set of units and owners for review, checking that each unit's ownership shares add up to 1/1 before anything is created - no more typing units and owners in by hand
- Board members and company/association details
- An opt-in phonelist so residents can find each other
- Custom fields: attach arbitrary typed fields (text, number, choice list, date, yes/no) to users, units, adverts, board members, entrances and fault reports
- User and group management with granular, per-feature permissions
- Configurable e-mail templates for system notifications, with a background sending queue
- A small admin REST API for creating units, owners and unit/owner assignments

### :bust_in_silhouette: Personal settings
- Profile editing, password change, interface language switch
- A "my units" overview so residents can see what they own or rent

## 1 Installation

Make sure you have `uv` tool installed:
```
uv --version
```
If not, install it from: https://docs.astral.sh/uv/getting-started/installation/


Clone the project
```
git clone https://github.com/destrosvet/dumis.git
cd dumis
```

Install the dependencies
```
uv sync --no-dev
# in Linux
source .venv/bin/activate
# in Windows
source .venv/Scripts/activate
```

Create the configuration
```
cd svjis
python manage.py migrate
python manage.py svjis_setup --password <choose password for admin user>
```

> [!NOTE]
> To compile the translations, you will need to have the `gettext` utility installed - try `gettext --version`. If you don't have it, feel free to skip the next step, and the application will only be available in English.
```
python manage.py compilemessages
```

## 2 Starting application

```
python manage.py runserver
```

The application runs at the address http://127.0.0.1:8000/ with the user `admin` and the password is the one you entered earlier.

The method of starting mentioned is suitable for quickly testing the application on your computer or for developers. If you want to deploy Dumis on a production server, please read the [Django documentation](https://docs.djangoproject.com/en/5.0/howto/deployment/).

## 3 Parameterization

### 3.1 SVJ Data

The settings for SVJ data can be found in the application under the `Administration` section.

### 3.2 Email Sending Settings

Dumis uses email sending for various events, so the correct configuration of the email interface is essential for the application's functionality.

Create a new file `svjis/svjis/local_settings.py` and add the following configuration:

```
SECRET_KEY = 'production django secret'
TIME_ZONE = 'Europe/Prague'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'your smtp server'
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
EMAIL_PORT = 465
EMAIL_HOST_USER = 'username to your smtp server'
EMAIL_HOST_PASSWORD = 'password to your smtp server'
```

Email sending occurs in the background - the system stores emails in a queue for sending, see `Administration - pending messages`. To send messages, you need to run the following command:

```
python manage.py svjis_send_messages
```

During application testing, you can run it manually. In a production setup, you need to configure a system scheduler (like cron) to run it at certain intervals (for example, every 5 minutes).

## 4 Docker

You can also use `docker compose` to run the Dumis application. Here is an example with Postgres.

Create following directories and files:

```
mkdir -p ./svjis2-data/static
mkdir -p ./svjis2-data/media
echo "DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql','NAME': 'svjis_db','USER': 'svjis_user','PASSWORD': 'change-it','HOST': 'svjis-db','PORT': '5432',}}" > ./svjis2-data/local_settings.py
chmod -R ugo+rwx ./svjis2-data
```

Run docker compose:

```
docker compose up -d
```

If you run it for the first time and database is empty create basic parametrization including admin account:

```
docker exec svjis2_app bash -c "python svjis/manage.py svjis_setup --password <choose password for admin user>"
```

The application runs at the address http://127.0.0.1:8000/. You can stop it by command `docker compose down`

If you want to use different database or setup any other parameters modify local settings file `./svjis2-data/local_settings.py`.

> [!NOTE]
> By default application in container runs with `DEBUG = True`. If you want to run application in production edit `./svjis2-data/local_settings.py` file and override at least `SECRET_KEY`, `ALLOWED_HOSTS` and set `DEBUG = False`. You will aslo need `Nginx` or `Apache` reverse proxy which will be serving static files and will take care about tls certificate.

## 5 Troubleshooting

If you encounter any issues, feel free to open an [issue](https://github.com/destrosvet/dumis/issues).

## 6 Collaboration

Any form of collaboration is welcome. :octocat:
More information can be found in [CONTRIBUTING.md](CONTRIBUTING.md).

## 7 Credits

Dumis is built on top of [SVJIS](https://github.com/svjis/svjis2) by [Uhlíř](https://uhlir.me) - a huge thank you to the original project and its contributors. Please consider supporting the upstream project too.
