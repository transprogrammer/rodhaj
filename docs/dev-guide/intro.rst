============
Introduction
============

This is the documentation for Rodhaj, the modern ModMail bot for the transprogrammer server.

Software Requirements
=====================

Before you get started, please ensure you have the following installed:

- `Git <https://git-scm.com>`_
- `Python 3 <https://python.org>`_
- `Docker <https://docker.com>`_
- Discord Account + `App <https://discordpy.readthedocs.io/en/stable/discord.html>`_ 

If you are using Linux, the following dependencies will need to be installed:

- `libffi <https://github.com/libffi/libffi>`_
- `libnacl <https://github.com/saltstack/libnacl>`_
- `python3-dev <https://packages.debian.org/python3-dev>`_
- `libssl <https://github.com/openssl/openssl>`_

For a debian-based system, you can install them with the following command:

.. code-block:: bash

    $ apt install libffi-dev libnacl-dev python3-dev libssl-dev

.. caution:: 
    Rodhaj uses `uvloop <https://github.com/MagicStack/uvloop>`_ on Linux and MacOS
    and `winloop <https://github.com/Vizonex/Winloop>`_ on Windows. Replacing the default event loop
    with these Cython-based implementations provides a significant performance boost.
    Although Rodhaj is natively developed and deployed on Linux,
    Windows support should work but is not tested.

Setup
=====

**Rodhaj only supports Python 3.9 or higher**

.. important::
  - Ensure that you are in the root of the repo throughout this process and have the database running
    
  - Rodhaj also supports Poetry, but for simplicity, virtualenvs are demonstrated here instead

1. Fork and clone the repo

2. Create an virtualenv

.. code-block:: bash

   python3 -m venv rodhaj

3. Activate the virtualenv

.. code-block:: bash
  
  # Linux/MacOS
  $ source rodhaj/bin/activate

  # Windows
  $ rodhaj/Scripts/activate.bat

4. Install dependencies and set up pre-commit hooks

.. code-block:: bash

   pip install -r requirements-dev.txt \
   && pre-commit install

5. Copy over the ``config-example.yml`` template over to the ``bot`` directory. Modify the values as appropriate.

.. code-block:: bash

    cp config-example.yml bot/config.yml

6. Run the SQL migrations

.. code-block:: bash

    python3 bot/migrations.py init

7. In order to demonstrate, you can run the bot to test everything out

.. code-block:: bash

    python3 bot/launcher.py

Database
--------
    
The following SQL queries can be used to create the user and database:

.. code-block:: sql

    CREATE ROLE rodhaj WITH LOGIN PASSWORD 'somepass';
    CREATE DATABASE rodhaj OWNER rodhaj;
    CREATE EXTENSION IF NOT EXISTS pg_trgm;

.. note::
    
    This step is largely skipped if you are using Docker to run
    the PostgreSQL server. If you decide not to use Docker, you 
    will need to manually create the database as shown below

Using Docker
^^^^^^^^^^^^

If you decide to use Docker to run the local PostgreSQL server, then a
pre-built Docker Compose file is provided. Setup instructions are as follows:

1. Copy ``envs/docker.env`` to ``.env`` within the root of the repo. Modify as appropriate.

.. code-block:: bash

    cp envs/docker.env .env

2. Run the following command to start the PostgreSQL server

.. code-block:: bash

    docker compose -f docker-compose-dev.yml up -d

Extensions
==========

Rodhaj includes the following extensions as noted:

Prometheus Exporter
^^^^^^^^^^^^^^^^^^^

Rodhaj currently includes an `Prometheus <https://prometheus.io/>`_ exporter. 
This exporter is intended to be used in production environments, where
metrics surrounding ticket usage, bot health, and others would provide
valuable insight. This exporter can be enabled by setting the 
``rodhaj.prometheus.enabled`` key within ``config.yml``. 

.. note::

    Prometheus client libraries are listed within the
    ``requirements.txt`` file. By default, these libraries
    should be installed, but disabling the exporter will not 
    affect the usage of these libraries.
