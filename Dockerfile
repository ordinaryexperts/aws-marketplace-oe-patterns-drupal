FROM ubuntu:focal

ADD setup-env.sh /setup-env.sh
RUN bash /setup-env.sh
