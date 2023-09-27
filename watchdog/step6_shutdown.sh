#!/bin/bash

source ./.env


if [ -z $SHUTDOWN_WHEN_DONE ] || ! $SHUTDOWN_WHEN_DONE
then
  printf "%s [INF] Shutdown of cluster %s skipped according to environment variable setting.\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${OCP_CLUSTER}"
  exit 0
fi

printf "%s [INF] Shutting down cluster %s...\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${OCP_CLUSTER}"

# check notes status, stop nodes that are "running", continue until all nodes are running
while true
do

  states=(`aws ec2 describe-instances --filters "Name=tag:Name,Values=$OCP_CLUSTER*" --query=Reservations[].Instances[].[InstanceId,State.Name] | jq -r 'flatten[]'`)
  numstates=${#states[@]}

  all_stopped=true
  instance_ids=""
  instance_count=0
  pending_count=0
  for (( i=0; i<numstates; i+=2 ))
  do
    instance_id=${states[$i]}
    state=${states[(( $i + 1 ))]}
    instance_ids+="${instance_id} "
    instance_count=$(( $instance_count + 1))
    if [ $state == "stopped" ]
    then
      continue
    fi
    all_stopped=false

    if [ $state == "running" ]
    then
      printf "%s [INF] Stopping instance $instance_id ...\n" "$(date '+%Y-%m-%d %H:%M:%S')"
      state=`aws ec2 stop-instances --instance-ids $instance_id`
      printf "%s [INF] %s\n" "$(date)" "${state}"
    else
      pending_count=$(( $pending_count + 1 ))
    fi 
  done

  if $all_stopped
  then
    break
  fi

  if [ $pending_count != 0 ]
  then
    printf "%s [INF] Instances pending: %d / %d\n" "$(date '+%Y-%m-%d %H:%M:%S')" $pending_count $instance_count
  fi

  sleep 5s

done