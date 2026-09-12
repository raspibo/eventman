FROM mongo:latest
LABEL \
	maintainer="Davide Alberani <da@mimante.net>" \
	vendor="RaspiBO"

VOLUME ["/data"]

COPY run.sh /
ENTRYPOINT ["/run.sh"]
