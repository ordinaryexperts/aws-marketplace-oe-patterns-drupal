FROM ubuntu:24.04

ENV IN_DOCKER=true

COPY ubuntu_2404_appinstall.sh /tmp/ubuntu_2404_appinstall.sh
RUN bash /tmp/ubuntu_2404_appinstall.sh
RUN rm -f /tmp/ubuntu_2404_appinstall.sh
