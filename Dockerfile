# Dockerfile for droope/droopescan
# License AGPL
FROM python:3.14

LABEL org.label-schema.name="droopescan" \
    org.label-schema.description="A plugin-based scanner that aids security researchers in identifying issues with several CMS." \
    org.label-schema.url="https://pypi.org/project/droopescan/" \
    org.label-schema.vcs-url="https://github.com/droope/droopescan" \
    org.label-schema.maintainer="pedro@worcel.com" \
    org.label-schema.schema-version="1.0"

COPY . /app
WORKDIR /app
RUN pip install setuptools && \
    pip install -r requirements.txt 
ENV PYTHONPATH=/app
ENTRYPOINT ["droopescan"]
CMD ["--help"]
