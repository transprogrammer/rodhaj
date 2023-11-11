####################################################################################################
## Builder image
####################################################################################################
FROM python:3.11-slim-bookworm AS builder

ENV DEBIAN_FRONTEND=noninteractive 

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  curl \
  git \
  && apt-get clean

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN curl -sSL https://install.python-poetry.org | python -
ENV PATH="${PATH}:/root/.local/bin"

WORKDIR /rodhaj
COPY /pyproject.toml /rodhaj/
COPY /poetry.lock /rodhaj/

RUN poetry export --output requirements.txt --without-hashes --only main

####################################################################################################
## Final image
####################################################################################################
FROM python:3.11-slim-bookworm

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  tini \
  bash \
  netcat-traditional \
  libopus-dev \
  libffi-dev \
  libsodium-dev \
  git \
  && apt-get clean

WORKDIR /rodhaj
COPY /bot /rodhaj/bot/
COPY /bot/cogs /rodhaj/bot/cogs/
# COPY /bot/migrations /rodhaj/bot/migrations/
COPY /docker/start.sh /rodhaj/start.sh
COPY /docker/wait-for /rodhaj/wait-for

COPY --from=builder /rodhaj/requirements.txt /rodhaj/requirements.txt

RUN adduser --disabled-password --gecos "" rodhaj \
  && chown -R rodhaj:rodhaj /rodhaj \
  && chmod +x /rodhaj/start.sh \
  && chmod +x /rodhaj/wait-for

USER rodhaj

ENV PATH="${PATH}:${HOME}.local/bin"

RUN pip install --user -r requirements.txt

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["/rodhaj/start.sh"]

STOPSIGNAL SIGTERM

LABEL org.opencontainers.image.title="Rodhaj"
LABEL org.opencontainers.image.description="A discord modmail bot"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.source="https://github.com/transprogrammer/rodhaj"
