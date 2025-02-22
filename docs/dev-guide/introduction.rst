============
Introduction
============

Rodhaj is internally built with discord.py. This document introduces relevant concepts and instructions for this project.

Prerequisites
-------------

There are some tools that you would need to have installed before you continue. 
They are listed below:

- `Git <https://git-scm.com>`_
- `Python 3 <https://python.org>`_
- `Docker <https://docker.com>`_
- `Task <https://taskfile.dev>`_
- Discord Account + App

If you are using Linux, the following dependencies will need to be installed:

- `libffi <https://github.com/libffi/libffi>`_
- `libnacl <https://github.com/saltstack/libnacl>`_
- `python3-dev <https://packages.debian.org/python3-dev>`_
- `libssl <https://github.com/openssl/openssl>`_

For a debian-based system, you can install them with the following command:

.. code-block:: bash

    apt install libffi-dev libnacl-dev python3-dev libssl-dev

.. note::
    Rodhaj replaces the default event loop with `uvloop <https://github.com/MagicStack/uvloop>`_ on Linux and MacOS and `winloop <https://github.com/Vizonex/Winloop>`_ on Windows. 
    Replacing the default event loop with these libraries is how Rodhaj is able to be extremely performant.
    Although Rodhaj is natively developed for Linux and MacOS, Windows support has not been tested.

Setup
-----

.. important::
  
  Ensure that you are in the root of the repo throughout this process and have the database running

Step 1 - Clone the repo
^^^^^^^^^^^^^^^^^^^^^^^

In order to work on the project at all, you will need to fork and clone the repo

.. code-block:: bash

    git clone https://github.com/transprogrammer/rodhaj

Step 2 - Create a virtualenv
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is best to make a virtualenv to install all dependencies on their first.

.. code-block:: bash

    python3 -m venv .venv

Step 3 - Activate the virtualenv
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Linux/MacOS
    source .venv/bin/activate

    # Windows
    .venv/Scripts/activate.bat

Step 4 - Install dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We are going to be installing all of the development dependencies needed.
This includes `Lefthook <https://github.com/evilmartians/lefthook>`_, which is the Git hooks manager.

.. code-block:: bash

   pip install -r requirements-dev.txt \
   && lefthook install

Step 5 - Copying configuration templates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Rodhaj is configured by using a YAML configuration, which a template of it is included in the repo. 
We need to copy it over and modify the values as needed.

.. code-block:: bash

    cp config-example.yml bot/config.yml

Step 6 - Run the SQL migrations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Rodhaj includes an custom SQL migrations system that has been battle-tested, so that's what we need to set up. 
If this step doesn't work, just skip it for now.

.. code-block:: bash

    python3 bot/migrations.py init

Step 7 - Running Rodhaj
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to demonstrate, we are going to run our bot. The following command executes this.

.. code-block:: bash

    python bot/launcher.py


Once done, set up your testing server, invite your development bot, and verify that it works.

.. tip:: 

    If you have Task installed, you can use ``task bot`` as a shortcut.

Database
--------

The database used is PostgreSQL. By default, a Docker Compose file is included for spinning up these for development. 
Setup instructions are as follows:

Step 1 - Copy ``.env`` template
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Copy ``docker/example.env`` to ``.env`` within the docker folder. Modify as appropriate.

.. code-block:: bash

    cp docker/example.env docker/.env

Step 2 - Run the servers
^^^^^^^^^^^^^^^^^^^^^^^^

All you need to do is to run the following command.

.. code-block:: bash

    docker compose -f docker/docker-compose.dev.yml up -d

.. tip:: 

    If you have Task installed, you can use ``task dev-up`` as a shortcut.

Details
-------

Development Features
^^^^^^^^^^^^^^^^^^^^

Rodhaj includes an development mode allowing for continuous
reloading of extensions and library code. Once the file is saved, the 
module is reloaded and changes can be reflected. This can be enabled 
through the ``rodhaj.dev_mode`` key in the configuration file. In addition,
Jishaku is bundled with the bot, allowing for easy debugging and
faster development.

.. note::

    You may need to restart the bot entirely for
    some changes to be reflected.

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

Type Hinting
^^^^^^^^^^^^

Rodhaj actively uses `type hinting <https://docs.python.org/3/library/typing.html>`_ in order to verify for types before runtime.
`Pyright <https://github.com/microsoft/pyright>`_ is used to enforce this standard. Checks happen before you commit, and on Github actions.
These checks are activated by default on VSCode. Pyright is available as a LSP on Neovim.

Minimum supported Python versions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Rodhaj implements the `SPEC 0 <https://scientific-python.org/specs/spec-0000/>`_ standard. 
Spefically, Python versions over **3 years** are dropped after initial release.
