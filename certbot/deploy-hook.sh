#!/bin/sh

LETSENCRYPT_DIR=/etc/letsencrypt
DHPARAMS_PEM=${LETSENCRYPT_DIR}/dhparams.pem

if [ ! -e "${DHPARAMS_PEM}" ]; then
  openssl dhparam -out ${DHPARAMS_PEM} 2048
fi

cp ${LETSENCRYPT_DIR}/live/${MAIL_HOSTNAME}/fullchain.pem ${LETSENCRYPT_DIR}/live/fullchain.pem
cp ${LETSENCRYPT_DIR}/live/${MAIL_HOSTNAME}/privkey.pem ${LETSENCRYPT_DIR}/live/privkey.pem

# TODO:
# for SERVICE in postfix dovecot nginx; do
#   curl --silent -X POST http://dockerapi/services/${SERVICE}/restart
# done
