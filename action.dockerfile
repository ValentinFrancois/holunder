FROM python:3.10-slim

RUN apt-get update && apt-get install -y rsync && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip

ARG INSTALL_DIR=/install
COPY pyproject.toml ${INSTALL_DIR}/
COPY holunder/ ${INSTALL_DIR}/holunder/
RUN pip install -e ${INSTALL_DIR}

ENTRYPOINT ["holunder"]


