GitHub
======

Create SSH key
--------------

Enter the following command on the server without a passphrase:

`ssh-keygen -t rsa -b 4096 -f .ssh/github`

Add the public key to the authorized keys:

`cat .ssh/github.pub >> .ssh/authorized_keys`

Add Repository secrets
----------------------

* SSH_PRIVATE_KEY: content of the private key file
* SSH_USER: user to access the server
* SSH_HOST: hostname/ip-address of your server
* WORK_DIR: path to the directory containing the repository
* MAIN_BRANCH: name of the main branch (mostly main)

Add GitHub action
-----------------

.. code-block:: yaml

   on:
     push:
       branches:
         - main
     workflow_dispatch:
     
   jobs:
     run_pull:
       name: run pull
       runs-on: ubuntu-latest
       
       steps:
       - name: install ssh keys
         # check this thread to understand why its needed:
         # https://stackoverflow.com/a/70447517
         run: |
           install -m 600 -D /dev/null ~/.ssh/id_rsa
           echo "${{ secrets.SSH_PRIVATE_KEY }}" > ~/.ssh/id_rsa
           ssh-keyscan -H ${{ secrets.SSH_HOST }} > ~/.ssh/known_hosts

       - name: connect and pull
         run: ssh ${{ secrets.SSH_USER }}@${{ secrets.SSH_HOST }} "cd ${{ secrets.WORK_DIR }} && git checkout ${{ secrets.MAIN_BRANCH }} && git pull && exit"
       - name: cleanup
         run: rm -rf ~/.ssh
