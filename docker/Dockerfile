#Dockerfile
#Engineer: T Looby
#Date: 05/15/2023
#Description:  Dockerfile for building HEAT docker image as non-root user
#
#this script should only be run on dev machine
#script is not run directly, but is used when buildDocker bash
#script is run.  buildDocker script calls this file using syntax
#similar to this:
# docker build -t plasmapotential/heat -f ./Dockerfile ./github/source

# start from base
FROM ubuntu:22.10

LABEL maintainer="tlooby@cfs.energy"

# create new user
ARG HOST_USER=heatuser
ARG HOST_UID=1000
ARG HOST_GID=1000

RUN groupadd --gid ${HOST_GID} heatuser \
  && useradd --uid ${HOST_UID} --gid heatuser --create-home heatuser

# copy context
WORKDIR /home/heatuser
COPY --chown=${HOST_USER}:${HOST_GID} . .

# revert to root to install packages
USER root

# environment variables
ENV runMode docker
ENV AppDir /home/heatuser
ENV APPDIR /home/heatuser
ENV DEBIAN_FRONTEND noninteractive
ENV PYTHONPATH /usr/lib/freecad-python3/lib

#set up paths for libs
ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:/usr/lib/x86_64-linux-gnu/qt5
ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:/usr/lib/x86_64-linux-gnu/netgen
ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:/home/heatuser/opt/mafot/lib
#ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:/home/heatuser/opt/paraview/lib #comment to prevent qt5 conflicts
ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:/home/heatuser/opt/openfoam/lib
ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:/home/heatuser/opt/openfoam/platforms/linux64GccDPInt32Opt/lib
ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:/home/heatuser/opt/openfoam/platforms/linux64GccDPInt32Opt/lib/sys-openmpi
ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:/home/heatuser/opt/swak4foam/lib
ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:/home/heatuser/opt/openfoam/platforms/linux64GccDPInt32Opt/lib/dummy
ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:/home/heatuser/opt/open3d/lib:/home/heatuser/opt/open3d/lib/python_package

#set up paths for bins
ENV PATH $PATH:/home/heatuser/opt/mafot/bin
ENV PATH $PATH:/home/heatuser/opt/paraview/bin
ENV PATH $PATH:/home/heatuser/opt/openfoam/bin
ENV PATH $PATH:/home/heatuser/opt/openfoam/platforms/linux64GccDPInt32Opt/bin
ENV PATH $PATH:/home/heatuser/opt/swak4foam/bin
ENV PATH $PATH:/home/heatuser/opt/open3d/bin

# install system-wide deps for HEAT
RUN apt-get -yqq update
RUN apt-get -yqq upgrade
RUN apt-get -yqq install python3
RUN apt-get -yqq install python3-pip
RUN apt-get -yqq install python3-pkg-resources
RUN apt-get -yqq install python3-distutils
#RUN apt-get -yqq install mdsplus-python
RUN apt-get -yqq install software-properties-common
#freecad
RUN apt-get -yqq install libfreecad-python3-0.20
#RUN apt-get -yqq install libfreecad-python3-0.19
#RUN add-apt-repository ppa:freecad-maintainers/freecad-daily
#RUN apt-get update
#RUN apt-get install -yqq freecad-daily-python3
RUN apt-get -yqq install coreutils
RUN apt-get -yqq install libnglib-6.2
RUN apt-get -yqq install libcurl4
RUN apt-get -yqq install nano
RUN apt-get -yqq install git
RUN apt-get -yqq install gfortran
RUN apt-get -yqq install libunwind-dev
#3D plasmas
RUN apt-get -yqq install libopenmpi-dev
RUN apt-get -yqq install libhdf5-openmpi-dev
RUN apt-get -yqq install libnetcdf-dev
RUN apt-get -yqq install libnetcdff-dev 

RUN ln -s /usr/lib/x86_64-linux-gnu/libunwind.so /usr/lib/x86_64-linux-gnu/libunwind.so.1

RUN apt-get -yqq upgrade

# fetch app specific deps
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install --ignore-installed blinker
RUN python3 -m pip install -r requirements.txt

# expose port
EXPOSE 8050

# switch back to heatuser
USER heatuser

#make heat folder
RUN mkdir -p /home/heatuser/HEAT

# start app
CMD [ "python3", "./source/HEAT/launchHEAT.py", "--a", "0.0.0.0", "--p", "8050", "--m", "g" ]