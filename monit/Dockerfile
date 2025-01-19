FROM debian:bookworm-slim

RUN apt update && apt install -y \
    curl \
    bind9-dnsutils \
    monitoring-plugins-standard \
    monit \
    redis-tools

COPY --chmod=600 monitrc /etc/monit/monitrc
COPY conf /etc/monit/conf-enabled
COPY scripts /opt/monit/scripts

CMD ["monit", "-I", "-B"]
