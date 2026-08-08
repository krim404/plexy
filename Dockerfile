FROM python:3.14

LABEL name="Plexy"
LABEL authors="Felix and Krim"
LABEL description="Matrix bot for Plex and Ombi"

COPY requirements.txt /opt/
RUN pip3 install -r /opt/requirements.txt

COPY . /opt/
VOLUME ["/opt/config", "/opt/data"]

CMD [ "python3", "/opt/main.py" ]