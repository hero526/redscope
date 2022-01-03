#!/bin/bash

. ../config/install.conf

# STAP INSTALL
sudo apt install wget build-essential binutils-dev libelf-dev libdw-dev linux-image-$(uname -r)-dbgsym linux-headers-$(uname -r)
sudo wget -P /opt https://sourceware.org/systemtap/ftp/releases/systemtap-${STAP_VERSION}.tar.gz
cd /opt
sudo tar xf systemtap-${STAP_VERSION}.tar.gz
cd /opt/systemtap-${STAP_VERSION}
./configure
sudo make && sudo make install \
&& sudo stap -ve 'probe begin { log("hello world") exit () }'