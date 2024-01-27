============
Introduction
============

This is the documentation for Rodhaj, the modern ModMail bot for the transprogrammer server.

Software Requirements
=====================

Before you get started, please ensure you have the following installed:

- `Git <https://git-scm.com>`_
- `Python 3 <https://python.org>`_
- `Poetry <https://python-poetry.org>`_
- `Docker <https://docker.com>`_
- Discord Account + App 

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
    Ensure that you are in the root of the repo throughout this process
    and have the database running

1. Fork and clone the repo

2. Install dependencies and set up pre-commits

.. code-block:: bash

    poetry install \
    && poetry run pre-commit install

3. Copy over the ``config-example.yml`` template over to the ``bot`` directory. Modify the values as appropriate.

.. code-block:: bash

    cp config-example.yml bot/config.yml

4. Run the SQL migrations

.. code-block:: bash

    poetry run python bot/migrations.py init

5. In order to demonstrate, you can run the bot to test everything out

.. code-block:: bash

    poetry run python bot/launcher.py

Database
--------
    
The following SQL queries can be used to create the user and database:

.. code-block:: sql

    CREATE ROLE rodhaj WITH LOGIN PASSWORD 'somepass';
    CREATE DATABASE rodhaj OWNER rodhaj;

.. note::
    
    This step is largely skipped if you are using Docker to run
    the PostgreSQL server. If you decide not to use Docker, you 
    will need to manually create the database as shown below

Using Docker
^^^^^^^^^^^^

If you decide to use Docker to run the local PostgreSQL server, then a
pre-built Docker Compose file is provided. Setup instructions are as follows:

1. Copy ``envs/docker.env`` to ``docker-compose.env`` within the root of the repo. Modify as appropriate.

.. code-block:: bash

    cp envs/docker.env docker-compose.env

2. Run the following command to start the PostgreSQL server

.. code-block:: bash

    docker compose -f docker-compose-dev.yml up -d