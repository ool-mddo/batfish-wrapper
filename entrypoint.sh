#!/bin/sh

CWD=$(pwd)

# git config for demo
cd "${MDDO_GIT_ALLOWED_CONFIGS_REPOSITORY}" || exit
echo "# set safe directory: ${MDDO_GIT_ALLOWED_CONFIGS_REPOSITORY}"
git config --global --add safe.directory "${MDDO_GIT_ALLOWED_CONFIGS_REPOSITORY}"
echo "# check safe directory"
git config -l | grep safe

cd "$CWD" || exit

# exec rest-api server
python3 src/app.py
