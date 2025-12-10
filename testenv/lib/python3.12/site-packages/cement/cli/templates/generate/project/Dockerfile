FROM python:3.9-alpine
LABEL MAINTAINER="{{ creator }} <{{ creator_email }}>"
ENV PS1="\[\e[0;33m\]|> {{ label }} <| \[\e[1;35m\]\W\[\e[0m\] \[\e[0m\]# "

WORKDIR /src
COPY . /src
RUN pip install --no-cache-dir -r requirements.txt \
    && python setup.py install
WORKDIR /
ENTRYPOINT ["{{ label }}"]
