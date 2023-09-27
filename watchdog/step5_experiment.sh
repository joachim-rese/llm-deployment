#!/bin/bash

source ./.env

printf "%s [INF] Running experiment...\n" "$(date)"

cd $TESTTOOL_WORKDIR

exec ./$TESTTOOL_APP

printf "%s [INF] End of experiement.\n" "$(date)"
