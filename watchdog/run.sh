#! /bin/bash

execute() {
  printf "%s [INF] Running script %s...\n" "$(date)" $1
  /bin/bash ./$1

  if [ $? -ne 0 ]
  then
    printf "%s [ERR] Script %s failed.\n" "$(date)" $1
    /bin/bash ./step6_shutdown.sh
    exit 8
  fi

  exit 0
}


for script in "step1_reservation.sh" "step2_startup.sh" "step3_setup.sh" "step4_startpod.sh" "step5_experiment.sh" "step6_shutdown.sh"
do
  execute $script
done

