=================
Migrating to YAML
=================

Rodhaj now uses an new config format, YAML.
Previously, the project utilized an ENV file for configuration, but
due to issues such as the inability for better structured data and others,
the project has migrated to YAML.

The details of the motivation can be found in
`PR #59 <https://github.com/transprogrammer/rodhaj/pull/59>`_.

.. note::

    - ``*.yaml`` files are ignored and not read by the config loader. Ensure that your YAML file uses the ``*.yml`` file extension.
    - The config file is stored in the same location as the ``.env`` file. It will always be read under ``bot/config.yml``.
    
Changes
=======

Grouped entries
---------------

The bot token, and others are merged into one mapping. This mapping key is denoted
by ``rodhaj``. Any and all configuration options in relation to the bot can be found
under that mapping.

To illustrate, an example comparison of the old and new config format is shown below:

``.env``

.. code-block:: bash

    TOKEN=...
    DEV_MODE=False

``config.yml``

.. code-block:: yaml

    rodhaj:
        token: ...
        dev_mode: False # This key-value pair can also be removed to disable the dev mode feature

Rodhaj's Guild ID can now be set via the config
-----------------------------------------------

Instead of hardcoding the Guild ID into the code, to allow for flexibity in development,
the Guild ID can now be set via the config. This is acheived through the ``guild_id`` entry as illustrated.

.. code-block:: yaml

    rodhaj:
        guild_id: 1234567890 # This ID is the guild that is associated with Rodhaj for operations

PostgreSQL Connection URI
-------------------------

The PostgreSQL URI is mostly the same, but is now under the ``postgres_uri`` entry.