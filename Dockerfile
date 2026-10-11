FROM python:3.12-slim-bookworm AS dependencies
WORKDIR /build
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libcups2-dev && \
    rm -rf /var/lib/apt/lists/*
COPY requirements*.txt ./
RUN python -m pip wheel --wheel-dir /wheels \
    -r requirements-eventbrite.txt -r requirements-printing.txt

FROM python:3.12-slim-bookworm
LABEL maintainer="Davide Alberani <da@mimante.net>" vendor="RaspiBO"
EXPOSE 5242
VOLUME ["/eventman/data"]
RUN apt-get update && \
    apt-get install -y --no-install-recommends libcups2 && \
    rm -rf /var/lib/apt/lists/* && \
    useradd --system --home-dir /eventman --shell /usr/sbin/nologin eventman
COPY --from=dependencies /wheels /wheels
COPY requirements*.txt /requirements/
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels \
    -r /requirements/requirements-eventbrite.txt \
    -r /requirements/requirements-printing.txt && \
    rm -rf /wheels
WORKDIR /eventman
COPY --chown=eventman:eventman eventman_server.py monco.py utils.py ./
COPY --chown=eventman:eventman angular_app/index.html ./angular_app/index.html
COPY --chown=eventman:eventman angular_app/js/modern-app.js ./angular_app/js/modern-app.js
COPY --chown=eventman:eventman static/css/eventman-modern.css ./static/css/eventman-modern.css
COPY --chown=eventman:eventman data ./data
COPY --chown=eventman:eventman ssl/README.txt ./ssl/README.txt
COPY --chown=eventman:eventman templates/README.txt ./templates/README.txt
USER eventman
ENTRYPOINT ["python", "eventman_server.py", "--mongo_url=mongodb://mongo"]
