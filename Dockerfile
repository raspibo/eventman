FROM debian:stable-slim
LABEL \
	maintainer="Davide Alberani <da@mimante.net>" \
	vendor="RaspiBO"

EXPOSE 5242
VOLUME ["/eventman/data"]

RUN \
	apt-get update && \
	apt-get -y --no-install-recommends install \
		python3-cups \
		python3-dateutil \
		python3-pip \
		python3-pymongo \
		python3-tornado && \
	pip3 install --break-system-packages eventbrite && \
	useradd --system --home-dir /eventman --shell /usr/sbin/nologin eventman && \
	rm -rf /var/lib/apt/lists/*

COPY . /eventman

WORKDIR /eventman/
RUN chown -R eventman:eventman /eventman
USER eventman
ENTRYPOINT ["./eventman_server.py", "--mongo_url=mongodb://mongo"]
