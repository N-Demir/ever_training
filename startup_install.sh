#! /bin/bash
set -e

# Commands that need to be run by modal at runtime (usually because they require a volume)
# We don't need the volume though, so when this works we should be able to fold it into the image itself
cd /root
git clone https://github.com/N-Demir/viser.git

cd /root/viser
/opt/conda/bin/conda run -n ever pip uninstall -y viser

# only need to run these once
cd src/viser/client

export NVM_DIR="$HOME/.nvm"
mkdir -p "$NVM_DIR"
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm install 23.9.0
corepack prepare yarn@4.7.0 --activate
nvm use v23.9.0
corepack enable

yarn install && yarn build

cd /root/viser
/opt/conda/bin/conda run -n ever pip install -e .