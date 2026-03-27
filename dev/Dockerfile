FROM homeassistant/home-assistant:stable

RUN apk add inotify-tools

COPY ./start.sh /start.sh

ENTRYPOINT ["/start.sh"]
