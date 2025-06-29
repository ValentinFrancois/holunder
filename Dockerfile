FROM python:3.10-slim

ARG PROJECT=/srv/
WORKDIR $PROJECT

RUN pip install --upgrade pip

COPY pyproject.toml .
COPY holunder/ holunder/
RUN pip install -e .

ENTRYPOINT ["holunder"]


