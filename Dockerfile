FROM python:3.6-jessie

ENV CLOUD_SDK_REPO cloud-sdk-jessie
ENV GOROOT=/usr/local/go
ENV PATH=$PATH:$GOROOT/bin

# Setup builder
RUN mkdir /builder

COPY requirements.txt bot_the_builder.py template.sh setup.sh /builder/

RUN /builder/setup.sh