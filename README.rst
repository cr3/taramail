TaraMail
========

.. image:: https://github.com/taradix/taramail/workflows/test/badge.svg
       :target: https://github.com/taradix/taramail/actions
.. image:: https://github.com/taradix/taramail/workflows/deploy/badge.svg
       :target: https://mail.taram.ca

Communauté de Notre-Dame-du-Laus.

Setup
-----

docker compose run -it --rm -p 80 certbot certbot certonly -v --standalone --non-interactive --agree-tos --deploy-hook /deploy-hook.sh -d taram.ca -d mail.taram.ca
