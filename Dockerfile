FROM python:3-slim-bookworm

RUN apt update && apt install -y cron

RUN pip install domain-connect-dyndns

RUN echo "*/1 * * * * root /usr/bin/flock -n /tmp/ipupdate.lck /usr/local/bin/domain-connect-dyndns update --all --config /settings.txt > /proc/1/fd/1 2>/proc/1/fd/2" > /etc/cron.d/domain-connect-dyndns

CMD ["cron", "-f"]
