FROM python:3.11

COPY requirements.txt /requirements.txt
RUN pip3 install --upgrade pip && pip3 install -r /requirements.txt

RUN mkdir /video-subtitle-generator
WORKDIR /video-subtitle-generator
COPY video-subtitle-generator /video-subtitle-generator
