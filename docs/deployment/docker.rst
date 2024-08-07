======
Docker
======

.. warning::

    This method of deployment is only for internal use within the transprogrammer community.
    In addition, this deployment method is fairly advanced. This guide is only intended for internal
    documentation for possible deployment options.

Docker Compose can be used to run an Rodhaj instance in production. This will only work if you have access to the
Rodhaj Docker images.

Step 1 - Download required files
================================

Create a directory (e.g. ``./rodhaj``), which will hold all of the required files.

.. code-block:: bash

    mkdir ./rodhaj
    cd ./rodhaj

Download ``docker-compose.yml``, ``config.yml``, and ``example.env`` using the following commands:

.. code-block:: bash

    wget -O docker-compose.yml https://github.com/transprogrammer/rodhaj/releases/latest/download/docker-compose.yml \
    && wget -O config.yml https://github.com/transprogrammer/rodhaj/releases/latest/download/config-example.yml \
    && wget -O .env https://github.com/transprogrammer/rodhaj/releases/latest/download/example.env

.. note::

    Optionally, if you desired a full production version, then use the following commands to download
    ``docker-compose.prod.yml``, ``example.env``, and ``prometheus.yml``:

    .. code-block:: bash

        wget -O docker-compose.yml https://raw.githubusercontent.com/transprogrammer/rodhaj/main/docker/docker-compose.prod.yml \
        && wget -O prometheus.yml https://raw.githubusercontent.com/transprogrammer/rodhaj/main/docker/prometheus.yml \
        && wget -O .env https://github.com/transprogrammer/rodhaj/releases/latest/download/example.env

Step 2 - Populate ``.env`` and ``config.yml`` file with values
==============================================================

- Change ``DB_PASSWORD`` to a randomly generated password.
- Provide Rodhaj's bot token in ``config.yml``
- Change ``rodhaj.guild_id`` in ``config.yml`` to the server ID that Rodhaj is running on
- Modify the PostgreSQL URI used in ``config.yml`` to redirect to the database container and appropriate password

.. note::

    In order for Rodhaj to work container-wise, the IP aliases that is provided by the compose file
    must be used instead. For example, the URI would look like this (of course replace the password):

    .. code-block::

        postgresql://postgres:somepwd@database:5432/rodhaj

.. important::

    If you are running the full production version, please enable the Prometheus metrics
    found in Rodhaj's configuration

Step 3 - Start all containers
=============================

Assume that you are in the directory created in Step 1, run the following command to bring up Rodhaj entirely.

.. code-block::

    docker compose up -d

.. tip::

    If you are having issues downloading container images, you will need to authenticate to the Github Container 
    Registry. Steps can be found `here <https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#authenticating-to-the-container-registry>`_.

Step 4 - Upgrading
==================

.. danger::

    Although Rodhaj doesn't often update version-wise, there
    may be breaking changes between versions. Be careful and be 
    up-to-date with changes.

Upgrading Rodhaj is very simple. All you need to do is run the following commands below:

.. code-block:: bash

    docker compose pull && docker compose up -d