FROM python:3.8
WORKDIR /usr
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
ADD src /usr/src
WORKDIR /usr/src
