# Contributing

This document goes over the process of contributing, and the setup instructions.

## Development

### Software Requirements

- Git
- Poetry
- Python
- Docker
- Discord Account + App

> [!WARNING]
> Rodhaj is natively developed on Linux, and is known to work on Linux and MacOS. 
> Development should work on Windows but is highly untested.

### Setup Instructions

1. Ensure that you have a separate development bot and server before continuing. 

2. Fork and clone the repo

    ```bash
    git clone https://github.com/[username]/rodhaj
    ```

    Alternatively, you can use the `gh` tool to clone the repo:

    ```bash
    gh repo clone https://github.com/[username]/rodhaj
    ```

> [!NOTE]
> Ensure that you are in the cloned repo before continuing

3. Copy the ENV template into the `bot` directory

    ```bash
    cp envs/dev.env bot/.env
    ```

4. Install the dependencies

    ```bash
    poetry install
    ```

5. Configure the settings in the ENV file (Note that the user that is created in the Docker container is `rodhaj`)

6. Run the migrations

    If this is the first time setting up the PostgreSQL server:

    ```bash
    poetry run python bot/migrations.py init
    ```

    If you are already have migrations set, then upgrade:

    ```bash
    poetry run python bot/migrations.py upgrade
    ```

7. Launch the bot

    ```bash
    poetry run python bot/launcher.py
    ```

> Where are the slash commands? See the [FAQ](CONTRIBUTING.md#where-are-the-slash-commands)



### PostgreSQL Setup (If you are not using Docker)

If you are not using Docker, then you'll need to manually create and set up the database.
The following SQL queries set up the user and database

```sql
CREATE ROLE rodhaj WITH LOGIN PASSWORD 'somepass';
CREATE DATABASE rodhaj OWNER rodhaj;
```

You'll need to activate the `pg_trgm` extension within the `rodhaj` database.

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

## FAQ

### Where are the slash commands?

> TL;DR
> Manually sync using Umbra's Sync Command (`r>sync <guild_id`)

Unlike other frameworks, discord.py **does not** automatically sync slash commands to Discord. 
Slash commands are commands that need to be sent to Discord, and they take care of the rest.
As a result, you'll need to manually sync using [Umbra's Sync Command](https://about.abstractumbra.dev/discord.py/2023/01/29/sync-command-example.html),
which is included in the bot.
See [this gist](https://gist.github.com/No767/e65fbfdedc387457b88723595186000f) for more detailed information.