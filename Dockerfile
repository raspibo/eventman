FROM debian:stable-slim
LABEL \
	maintainer="Davide Alberani <da@erlug.linux.it>" \
	vendor="RaspiBO"

EXPOSE 5242

RUN \
	apt-get update && \
	apt-get -y install \
		python3-cups \
		python3-dateutil \
		python3-pip \
		python3-pymongo \
		python3-tornado && \
	pip3 install eventbrite && \
	rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/eventman/
COPY . /opt/eventman/

WORKDIR /opt/eventman/
ENTRYPOINT ["./eventman_server.py"]
CMD ["--debug"]
