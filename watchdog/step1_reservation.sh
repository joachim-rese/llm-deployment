#!/bin/bash

source ./.env

# check existing instances
./check_instance.sh
if [ $? == 0 ]
then
  printf "%s [WRN] Instance of type %s already running\n" "$(date)" $INSTANCE_TYPE
  exit 0
fi

states=`aws ec2 describe-capacity-reservations --filters "Name=instance-type,Values=${INSTANCE_TYPE}" --query CapacityReservations[].State | jq -r '.[]'`

for state in $states
do
  if [ $state == "active" -o $state == "pending" ]
  then
    printf "%s [WRN] Reservation for instance type %s already in state %s\n" "$(date)" $INSTANCE_TYPE "${state}"
    exit 0
  fi
done

printf "%s [INF] Issuing capacity reservation request...\n" "$(date)"

while true
do
  # calculate end time (1 hour from now)
  end_sec=$(((`date +%s`) + 3600))
  end_date=`date -u -Iseconds --date="@${end_sec}"`
  aws ec2 --region $REGION create-capacity-reservation --end-date $end_date --end-date-type limited --instance-type $INSTANCE_TYPE --instance-platform Linux/UNIX --availability-zone $AVAILABILITY_ZONE --instance-count 1
  if ! [ $? -ne 0 ]
  then
    break
  fi
  sleep 1m
done


printf "%s [INF] Waiting for active state...\n" "$(date)"

states=`aws ec2 describe-capacity-reservations --filters "Name=instance-type,Values=${INSTANCE_TYPE}" --query CapacityReservations[].State | jq -r '.[]'`

for state in $states
do
  if [ $state == "active" ]
  then
    exit 0
  elif [ $state != "pending" ]
  then
    printf "%s [ERR] Capacity request has unexpected state %s.\n" "$(date)" "${state}"
    exit 8
  fi
  sleep 1m
done

printf "%s [INF] Reservation request is active now.\n" "$(date)"

exit 0
