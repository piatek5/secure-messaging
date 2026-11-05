# secure-messaging

A small end-to-end encrypted messaging web app. All encryption happens in the browser with WebCrypto, so the server only stores ciphertext and wrapped keys, and never sees a password or a message. The backend is Flask with SQLite, served by gunicorn behind nginx.

- Password never leaves the browser. It is stretched with PBKDF2 and split with HKDF into a login token and a key that protects private keys.
- Every message gets its own AES-GCM key, wrapped separately for the recipient and the sender with X25519, and is signed with Ed25519.
- Private keys stay non-extractable and only in memory, so reloading the page asks for password again.
- Fingerprints let two people compare keys, and the app warns you if a contact's keys change.

## Requirements

- [Docker](https://docs.docker.com/get-docker/) with Compose
- [mkcert](https://github.com/FiloSottile/mkcert)
- A browser with X25519 and Ed25519 support in WebCrypto (tested in Chromium)

For development, also:

- Python 3.15
- [uv](https://docs.astral.sh/uv/)

## Setup

Create a local certificate. Run mkcert on the machine your browser runs on, so that the browser trusts it:

```sh
mkcert -install
mkdir certs
mkcert -cert-file certs/localhost+1.pem -key-file certs/localhost+1-key.pem localhost 127.0.0.1
```

Create a `.env` file with a secret key:

```sh
echo "FLASK_SECRET_KEY=$(openssl rand -hex 32)" > .env
```

## Running

```sh
docker compose up --build -d   # build and start in the background
docker compose logs -f         # follow the logs
docker compose down            # stop (add -v to also delete the database)
```

Then open <https://localhost>. Migrations run on start, and the database lives in the `app-data` volume.

Use one account per browser profile, because tabs share the session cookie. To try two users at once, use a regular window and a private one.

## Project layout

```
src/secure_messaging/
  __init__.py     app factory and config
  api.py          JSON API
  models.py       users and messages
  extensions.py   database and migrations setup
  static/         page and browser code
    js/           crypto, identity, contacts, messages, API calls
migrations/       database migrations
nginx/            TLS, reverse proxy and security headers
tests/            pytest suite
```

## Development

```sh
uv sync                  # install dependencies
uv run flask db upgrade  # create the local database
uv run flask run         # http://localhost:5000, reads .env
uv run pytest            # tests
uv run ruff check --fix  # lint and autofix
uv run ruff format       # format
uv run pyright           # type check
```

## Planned additions

- Rate limiting on login and registration, using Redis
- Server-side sessions, so logging out really ends a session
- Sending files
- Deleting messages
- Random user IDs instead of sequential ones
- Better handling of several accounts or tabs in one browser
- Two-factor login with TOTP
