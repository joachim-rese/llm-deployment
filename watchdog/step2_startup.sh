#!/bin/bash

source ./.env

printf "%s [INF] Starting cluster %s...\n" "$(date)" "${OCP_CLUSTER}"

# check notes status, start nodes that are "stopped", continue until all nodes are running
while true
do

  states=(`aws ec2 describe-instances --filters "Name=tag:Name,Values=$OCP_CLUSTER*" --query=Reservations[].Instances[].[InstanceId,State.Name] | jq -r 'flatten[]'`)
  numstates=${#states[@]}

  all_running=true
  instance_ids=""
  instance_count=0
  pending_count=0
  for (( i=0; i<numstates; i+=2 ))
  do
    instance_id=${states[$i]}
    state=${states[(( $i + 1 ))]}
    instance_ids+="${instance_id} "
    instance_count=$(( $instance_count + 1))
    if [ $state == "running" ]
    then
      continue
    fi
    all_running=false

    if [ $state == "stopped" ]
    then
      printf "%s [INF] Starting instance $instance_id ...\n" "$(date)"
      state=`aws ec2 start-instances --instance-ids $instance_id`
      printf "%s [INF] %s\n" "$(date)" "${state}"
    else
      pending_count=$(( $pending_count + 1 ))
    fi 
  done

  if $all_running
  then
    break
  fi

  if [ $pending_count != 0 ]
  then
    printf "%s [INF] Instances pending: %d / %d\n" "$(date)" $pending_count $instance_count
  fi

  sleep 5s

done


printf "%s [INF] All %d nodes are running.\n" "$(date)" $instance_count

while true
do
  states=(`aws ec2 describe-instance-status --instance-ids $instance_ids --query=InstanceStatuses[].[InstanceStatus.Status,SystemStatus.Status] | jq -r 'flatten[]'`)

  if [ ${#states[@]} -lt $(( $instances_count )) ]
  then
    printf "%s [ERR] Cannot determine status of some nodes (%d expected, %d found).\n" "$(date)" $(( $instances_count * 2)) ${#states[@]}
  fi

  ok=0
  initializing=0
  others=0
  for state in "${states[@]}"
  do
    if [ $state == "ok" ]
    then
      ok=$(( $ok + 1 ))
    elif [ $state == "initializing" ]
    then
      initializing=$(( $initializing + 1))
    else
      others=$(( $others + 1))
    fi
  done

  if [ $initializing == 0 -a $others == 0 ]
  then
    break
  fi

   printf "%s [INF] Node status (2 per node): %d ok, %d initializing, %d others.\n" "$(date)" $ok $initializing $others

   sleep 10s
done

printf "%s [INF] All nodes are reachable.\n" "$(date)"

exit 0
