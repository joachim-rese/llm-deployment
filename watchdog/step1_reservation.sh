#! /bin/bash

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
  if [ $state == "active" -o $state == "pending" -o $state == "cancelled" ]
  then
    printf "%s [WRN] Reservation for instance type %s already in state %s\n" "$(date)" $INSTANCE_TYPE "${state}"
    exit 0
  fi
done

printf "%s [INF] Issuing capacity reservation request...\n" "$(date)"

while true
do
  aws ec2 --region $REGION create-capacity-reservation --instance-type $INSTANCE_TYPE --instance-platform Linux/UNIX --availability-zone $AVAILABILITY_ZONE --instance-count 1 --debug
  if ! [ $? -ne 0 ]
  then
    break
  fi
  sleep 1m
done


printf "%s [INF] Waiting for active state..." "$(date)"

states=`aws ec2 describe-capacity-reservations --filters "Name=instance-type,Values=${INSTANCE_TYPE}" --query CapacityReservations[].State | jq -r '.[]'`

for state in $states
do
  if [ $state == "active" ]
  then
    exit 0
  elif [ $state != "pending" ]
  then
    printf "%s [ERR] Capacity request has unexpected state %s." "$(date)" "${state}"
    exit 8
  fi
  sleep 1m
done

exit 0

