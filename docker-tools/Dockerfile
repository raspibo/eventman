FROM mongo:latest
LABEL \
	maintainer="Davide Alberani <da@erlug.linux.it>" \
	vendor="RaspiBO"

VOLUME ["/data"]

COPY run.sh /
ENTRYPOINT ["/run.sh"]
