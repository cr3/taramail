FROM alpine:3.20

RUN apk add --update --no-cache \
  curl \
  bind-tools \
  unbound \
  bash \
  openssl \
  drill \
  tzdata \
  && install -d -g unbound -m 775 /etc/unbound

COPY healthcheck.sh /
HEALTHCHECK --interval=30s --timeout=30s CMD [ "/healthcheck.sh" ]

COPY docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]

EXPOSE 53/udp 53/tcp

CMD ["/usr/sbin/unbound"]
