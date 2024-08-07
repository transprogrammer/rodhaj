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

Download the necessary archive for getting started. This archive contains all
of the files needed to get started. These are provided either in ``.zip`` or ``.tar.gz``
formats. 

.. code-block:: bash

    wget https://github.com/transprogrammer/rodhaj/releases/latest/download/rodhaj-docker.tar.gz

    # .zip version download
    wget https://github.com/transprogrammer/rodhaj/releases/latest/download/rodhaj-docker.zip

We need to unpack the archive in order to access the files. The following commands should do that.

.. code-block:: bash

    tar -xvzf rodhaj-docker.tar.gz

    # .zip version unpacking
    unzip rodhaj-docker.zip

Once we have the files, we can now ``cd`` into the new extracted archive. 

.. code-block:: bash
    
    cd rodhaj-docker

.. important:: 

    Throughout the rest of the guide, the next steps assume that 
    you are in the ``rodhaj-docker`` directory.
    
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