FROM ubuntu:focal

COPY setup-env.sh /tmp/setup-env.sh
RUN bash /tmp/setup-env.sh

COPY . /code
WORKDIR /code/cdk
RUN pip3 install -r requirements.txt
