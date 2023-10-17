#!/bin/bash

# Run script "argv1" and shutdown cluster in case of an error
execute() {
  printf "%s [INF] ***** Running script %s *****\n" "$(date '+%Y-%m-%d %H:%M:%S')" $1
  /bin/bash ./$1

  if [ $? -ne 0 ]
  then
    printf "%s [ERR] Script %s failed.\n" "$(date '+%Y-%m-%d %H:%M:%S')" $1
    /bin/bash ./step6_shutdown.sh
    exit 8
  fi
}

#
# Run all scripts with prefix "step" (note: by default, ls lists files in alphabethical order)
#
sed -i '/^SHUTDOWN_WHEN_DONE=/d' .env

regex='step([0-9]*)'
for script in $(ls -1 step*.sh)
do
  if [[ ($# -eq 0) ]]
  then
    execute $script
  else
    if [[ $script =~ $regex ]]
    then
      if [[ $1 == *"${BASH_REMATCH[1]}"* ]]
      then
        execute $script
      else 
        printf "%s [INF] ***** Skipping script %s (not in \"%s\") *****\n" "$(date '+%Y-%m-%d %H:%M:%S')" $script $1
      fi 
    fi 
  fi 
done
