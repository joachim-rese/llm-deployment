#!/bin/bash

source ./.env

printf "%s [INF] Running experiment...\n" "$(date '+%Y-%m-%d %H:%M:%S')"

source $TESTTOOL_VENV/bin/activate

cd $TESTTOOL_WORKDIR

exec ./$TESTTOOL_APP

printf "%s [INF] End of experiement.\n" "$(date '+%Y-%m-%d %H:%M:%S')"
