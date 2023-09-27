#!/bin/bash

source ./.env

printf "%s [INF] Starting cluster %s...\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${OCP_CLUSTER}"

# check notes status, start nodes that are "stopped", continue until all nodes are running
while true
do

  states=(`aws ec2 describe-instances --filters "Name=tag:Name,Values=$OCP_CLUSTER*" --query=Reservations[].Instances[].[InstanceId,State.Name] | jq -r 'flatten[]'`)
  numstates=${#states[@]}

  all_running=true
  instance_ids=""
  instance_count=0
  pending_count=0
  terminated_count=0
  started_count=0
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

    if [ $state == "terminated" ]
    then
      terminated_count=$(( $terminated_count + 1 ))
      instance_count=$(( $instance_count - 1))
      continue
    fi

    all_running=false
    if [ $state == "stopped" ]
    then
      printf "%s [INF] Starting instance $instance_id ...\n" "$(date '+%Y-%m-%d %H:%M:%S')"
      state=`aws ec2 start-instances --instance-ids $instance_id`
      printf "%s [INF] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${state}"
      started_count=$(( $started_count + 1 ))
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
    printf "%s [INF] Instances pending: %d / %d (%d terminated) \n" "$(date '+%Y-%m-%d %H:%M:%S')" $pending_count $instance_count $terminated_count
  fi

  sleep 5s
done

printf "%s [INF] All %d nodes are running.\n" "$(date '+%Y-%m-%d %H:%M:%S')" $instance_count

if [ -z $SHUTDOWN ] || [ $SHUTDOWN == "auto" ]
then
  if [ $((instance_count - started_count)) -ge 2 ]
  then
    shutdown_action=false
  else
    shutdown_action=true
  fi
else
  shutdown_action=$SHUTDOWN
fi

if $shutdown_action
then
  printf "%s [INF] Shutting down cluster when done.\n" "$(date '+%Y-%m-%d %H:%M:%S')"
else
  printf "%s [INF] Keeping cluster up and running when done.\n" "$(date '+%Y-%m-%d %H:%M:%S')"
fi

if [ -z $SHUTDOWN_WHEN_DONE ]
then
  if [[ $(tail -c1 .env | wc -l) -eq 0 ]]
  then
    newline='\n'
  fi
  echo -e "${newline}SHUTDOWN_WHEN_DONE=${shutdown_action}" >> .env
else
  sed -i "/SHUTDOWN_WHEN_DONE/s/=.*$/=${shutdown_action}/" .env
fi

while true
do
  states=(`aws ec2 describe-instance-status --instance-ids $instance_ids --query=InstanceStatuses[].[InstanceStatus.Status,SystemStatus.Status] | jq -r 'flatten[]'`)

  if [ ${#states[@]} -lt $(( $instances_count )) ]
  then
    printf "%s [ERR] Cannot determine status of some nodes (%d expected, %d found).\n" "$(date '+%Y-%m-%d %H:%M:%S')" $(( $instances_count * 2)) ${#states[@]}
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
      if  [ $state != "terminated" ]
      then
        others=$(( $others + 1))
      fi
    fi
  done

  if [ $initializing == 0 -a $others == 0 ]
  then
    break
  fi

   printf "%s [INF] Node status (2 per node): %d ok, %d initializing, %d others.\n" "$(date '+%Y-%m-%d %H:%M:%S')" $ok $initializing $others

   sleep 10s
done

printf "%s [INF] All nodes are reachable.\n" "$(date '+%Y-%m-%d %H:%M:%S')"

exit 0
