HEAT via the docker container
#############################
This page provides information on downloading and running HEAT from the docker
container.

Installing the docker container
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To run the HEAT docker container, the user will need docker and docker-compose
installed on the local machine.

To download docker and docker-compose
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

First download docker (docker engine)
 - (`<https://docs.docker.com/engine/install/>`_)

Next, set the user up for running docker.  This includes adding the user to the
docker group (example link below for Linux)
 - (`<https://docs.docker.com/engine/install/linux-postinstall/>`_)

Install docker-compose, which is necessary to configure the HEAT environment
  - (`<https://docs.docker.com/compose/install/>`_)

Download HEAT docker container
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now that docker is installed, you will need to pull the HEAT docker container
from docker hub.  The HEAT docker hub page is located here:
 - (`<https://hub.docker.com/r/plasmapotential/heat>`_)

To pull from docker hub, execute the following command::

    docker pull plasmapotential/heat:<tag>

where <tag> reflects the latest HEAT version (ie v3.0, v4.1, or whatever version you want)

Download HEAT source code from github
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To run HEAT using docker, it can be useful to have several files from the HEAT
github page that set up the docker environment.  The easiest way to download the
HEAT source code is to create a new directory, and pull the source using git::

    cd <sourcePath>
    git clone https://github.com/plasmapotential/HEAT.git

Where <sourcePath> is the path where you want to save HEAT  Once you have the
HEAT source code downloaded, the files you need to run docker are located in the
docker directory, <sourcePath>/docker

If you already have the HEAT source code downloaded, then you can pull the latest with:

.. code-block:: bash

    git pull

If you want to force the pull to overwrite your local changes:

.. code-block:: bash

    git reset --hard HEAD


Starting HEAT with docker
^^^^^^^^^^^^^^^^^^^^^^^^^
In HEAT v2+ here are two ways a user can run HEAT:
 - In an html5 based Graphical User Interface (GUI)
 - From a Terminal User Interface (TUI)

Starting HEAT from both interfaces is covered in the following sections.  For
both modes, the user needs docker, docker-compose, and the HEAT source code
installed.  Additionally, the following video provides an introduction to using
HEAT from the docker container:


    .. raw:: html

        <div style="position: relative; padding-bottom: 2%; height: 0; overflow: hidden; max-width: 100%; height: auto;">
            <iframe width="560" height="315" src="https://www.youtube.com/embed/ygNJRAYitAI" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
        </div>


Permissions in Docker on Linux
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
When a user launches an application in a docker container, that application is run as root inside the container.
This can be problematic if the container writes files to the host OS, as the user id (UID) and group id (GID)
inside the container may not match up with the UID and GID of the user on the host.  Newer versions of docker
intelligently pass the UID and GID into the container, but older versions do not.  The HEAT source code contains
a bash script, runDockerCompose, that can pass the UID and GID into the container so that all files written during
the HEAT run will be saved with the user's UID/GID.  This happens in the following code:

.. code-block:: bash

    #check for docker group and load into ${dockerGID}
    if [ $(getent group docker) ]; then
      echo "docker group exists. setting dockerGID env var..."
      export dockerGID="$(getent group docker | cut -d: -f3)"
    else
      echo "'docker' group does not exist."
      echo "If you continue HEAT files will be saved under root group!"
      echo "It is recommended (but not required) that you create group"
      echo "'docker' and add yourself to it before running HEAT."
    fi
    #get user id
    if [ $(getent group docker) ]; then
      echo "copying UID for user into docker container"
      export dockerUID="$(echo $UID)"
    else
      echo "could not copy user ID into docker."
      echo "files will be saved as root:root !"
    fi


If your docker configuration has UID/GID mapping enabled, then you can comment out those
aforementioned lines in runDockerCompose.


It is also possible to pass environment variables from your local session into the docker container
using the docker compose recipe file, docker-compose.yml .  To achieve this, you would first need
to determine your UID / GID and then uncomment the relevant lines in docker-compose.yml:

.. code-block:: yaml

       #environment:
       - dockerUID=$dockerUID
       - dockerGID=$dockerGID
       - UID=$dockerUID
       - GID=$dockerGID

For the latest version of docker, the UID and GID are passed into the container
automatically.  More information on this can be found here:  https://docs.docker.com/engine/security/userns-remap/

If you are unsure if your version of docker will do UID mapping, its best to just run a test.  First, get the UID
on the host (echo $UID), and then launch the docker container directly into bash mode and perform the same test:

.. code-block:: bash

      docker-compose run HEAT /bin/bash



Start HEAT in GUI mode
^^^^^^^^^^^^^^^^^^^^^^
To start HEAT using the graphical user interface, perform the following steps:

  1) Navigate to the HEAT source code docker directory, <sourcePath>/docker
  2) Once in the docker directory, make sure the last 4 lines of runDockerCompose appear as follows::

.. code-block:: yaml

      #run docker compose
      docker-compose up
      #run docker compose interactively (for terminal mode)
      #docker-compose run HEAT /bin/bash


  3) Run docker compose from within the docker directory:

.. code-block:: bash

      docker-compose up

Start HEAT in TUI mode
^^^^^^^^^^^^^^^^^^^^^^
To start HEAT using the terminal user interface, perform the following steps:

  1) Navigate to the HEAT source code docker directory, <sourcePath>/docker
  2) Edit the docker-compose.yml recipe file.  Under the volumes section,
     the user can bind directories on their local host machine into the docker
     container.  For each of these lines, the host path and container path are
     in the following format:

        <hostPath>:<containerPath>
     You should not need to edit the <containerPath>, but you will need to edit
     the <hostPath>.  For example, to bind the HEAT source code that you
     downloaded from github at the path <sourcePath> into the container, you
     would have the following line under volumes in the recipe::

          - <sourcePath>:/root/source/HEAT
     You should uncomment the lines that correspond to the local packages that
     you have installed.  The HEAT data directory should always be uncommented
     and binded::

          - ${HOME}/HEAT:/root/HEAT
     For running in terminal mode, you will need to uncomment the line that
     binds your local batchMode directory into the container::

          - <batchModePath>:/root/terminal
     where <batchModePath> is the directory where your batchFile lives.

  3) In the docker directory, make sure the last line of runDockerCompose appears as follows:

  .. code-block:: yaml

    #run docker compose
    #docker-compose up
    #run docker compose interactively (for terminal mode)
    docker-compose run HEAT /bin/bash


  4) Run docker compose from within the docker directory:

  .. code-block:: bash

    ./runDockerCompose


  5) Running docker-compose in terminal mode launches a bash terminal inside the
     container.  Once inside the container, navigate to the HEAT source code
     directory::

      cd /root/source/HEAT/
  6) Once in the source directory, launch HEAT using the batchFile.dat that
     was binded into the container in step 2)::

      python3 launchHEAT.py --m t --f /root/terminal/batchFile.dat
    
     There are also convenience bash scripts that run this command for you::

      ./runTerminalMode

