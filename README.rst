Taram
=====

Communauté de Notre-Dame-du-Laus.

Setup
-----

docker compose run -it --rm -p 80 certbot certbot certonly -v --standalone --non-interactive --agree-tos --deploy-hook /deploy-hook.sh -d taram.ca -d mail.taram.ca
