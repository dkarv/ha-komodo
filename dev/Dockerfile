FROM homeassistant/home-assistant:beta

RUN apk add inotify-tools

COPY ./start.sh /start.sh

ENTRYPOINT ["/start.sh"]
