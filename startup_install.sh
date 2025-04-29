#! /bin/bash
set -e

# Commands that need to be run by modal at runtime (usually because they require a volume)

cd /root/viser

# only need to run these once
# cd src/viser/client
# yarn install && yarn build

git pull
/opt/conda/bin/conda run -n ever pip install -e .