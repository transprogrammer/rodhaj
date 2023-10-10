# rodhaj
proto-repo for discord app

**later down the road, pls do not push to main branch directly**

## Stuff that needs to be done

- [x] Paginators
- [ ] R. Danny migrations or asyncpg-trek
- [ ] The features

## Getting Started

### Preface on Slash Commands

Unlike other frameworks, discord.py does not automatically sync slash commands (if you want to learn more why, see [this and why Noelle is heavily against it](https://github.com/No767/Zoee#preface-on-slash-commands-and-syncing)). So the way to sync is by using an prefixed commands, which is [Umbra's Sync Command](https://about.abstractumbra.dev/discord.py/2023/01/29/sync-command-example.html). More than likely you'll need to read up on how this slash command works in order to get started. In short, you'll probably want to sync your test bot to the guild instead (as demostrated here):

```
# Replace 1235 with your guild id
r>sync 1235
```

### PG Setup
If you want to run postgres on an docker compose stack,
then all you need to do is to make an `.env` file in the root of the repo,
and add these:

```bash
POSTGRES_PASSWORD=password
POSTGRES_USER=user
POSTGRES_DB=user
```

The values above set up the root postgres user. Ideally you will want to make an new user, which can be done like so:

```sql
CREATE ROLE rodhaj WITH LOGIN PASSWORD 'somepass';
CREATE DATABASE rodhaj OWNER rodhaj;
```

### Setup Instructions

You must have these installed:

- Poetry
- Python
- Git
- PostgreSQL

1. Clone the repo or use it as a template.
2. Copy over the ENV file template to the `bot` directory

    ```bash
    cp envs/dev.env bot/.env
    ```
3. Install the dependencies

    ```bash
    poetry install
    ```

4. Configure the settings in the ENV (note that configuring the postgres uri is required)

5. Run the bot
    
    ```bash
    poetry run python bot/launcher.py
    ```

6. Once your bot is running, sync the commands to your guild. You might have to wait a while because the syncing process usually takes some time. Once completed, you should now have the `CommandTree` synced to that guild. 

    ```
    # Replace 12345 with your guild id
    r>sync 12345 
    ```
7. Now go ahead and play around with the default commands. Add your own, delete some, do whatever you want now.

#### License

<sup>
Licensed under either of <a href="LICENSE-APACHE">Apache License, Version
2.0</a> or <a href="LICENSE-MIT">MIT license</a> at your option.
</sup>

<br>

<sub>
Unless you explicitly state otherwise, any contribution intentionally submitted
for inclusion in Rodhaj by you, as defined in the Apache-2.0 license, shall be
dual licensed as above, without any additional terms or conditions.
</sub>
