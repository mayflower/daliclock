# Melt

A Wear OS watchface with connected, curve-based digit morphing, inspired by
xdaliclock. Target: Watch Face Format 4 on Wear OS 6 / API 36 or newer.

## Status

The repository and local development environment are prepared. The watchface
has not been implemented yet. Successful sample builds described in
[SETUP.md](SETUP.md) verify the toolchain, not Melt's behavior.

## Start here

- [prompts.md](prompts.md): complete product specification and five implementation steps,
  copied unchanged from the supplied prompt set.
- [AGENTS.md](AGENTS.md): repository working agreements and implementation constraints.
- [SETUP.md](SETUP.md): installed tools, pinned versions, validation commands,
  and the tested Wear OS emulator configuration.

On the prepared machine, from this directory:

```sh
source .env.local.sh
source .venv/bin/activate
```

To recreate the Python environment with Python 3.13:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

The local activation file, SDK, virtual environment, external validation tools,
and sample artifacts are not committed. See SETUP.md for their locations.
Application build commands and the Gradle wrapper will be added with the
implementation.

## Intended implementation

Locally stored curves for all ten digits feed a small Python geometry library.
The preview and WFF exporter use the same sampled lines. Shared points have one
native animation owner; connected endpoints follow through WFF references.
The installed watchface is a resource-only package rendered by Wear OS.

The product shows HH:MM, optional morphing seconds enabled by default, an
optional date, three color themes, system 12/24-hour time, and German/English
editor labels. Always-on shows the current static hours and minutes.
