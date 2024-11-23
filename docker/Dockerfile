####################################################################################################
## Final image
####################################################################################################
FROM python:3.13-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  bash \
  git \
  netcat-traditional \
  tini \
  gcc \
  && apt-get clean

WORKDIR /rodhaj
COPY /bot /rodhaj/bot/
COPY /docker/start.sh /rodhaj/start.sh
COPY /docker/wait-for /rodhaj/wait-for
COPY /requirements.txt /rodhaj/requirements.txt

RUN adduser --disabled-password --gecos "" rodhaj \
  && chown -R rodhaj:rodhaj /rodhaj \
  && chmod +x /rodhaj/start.sh \
  && chmod +x /rodhaj/wait-for

USER rodhaj

ENV PATH="${PATH}:/home/rodhaj/.local/bin"

RUN pip install --user -r requirements.txt

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["/rodhaj/start.sh"]

STOPSIGNAL SIGTERM

LABEL org.opencontainers.image.title="Rodhaj"
LABEL org.opencontainers.image.description="A improved, modern version of ModMail for the transprogrammer community"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.source="https://github.com/transprogrammer/rodhaj"
