#!/bin/bash

source ./.env

# check existing instances
./check_instance.sh
if [ $? == 0 ]
then
  printf "%s [WRN] Instance of type %s already running\n" "$(date '+%Y-%m-%d %H:%M:%S')" $INSTANCE_TYPE
  exit 0
fi

# check existing reservation
states=`aws ec2 describe-capacity-reservations --filters "Name=instance-type,Values=${INSTANCE_TYPE}" --query CapacityReservations[].State | jq -r '.[]'`

for state in $states
do
  if [ $state == "active" -o $state == "pending" ]
  then
    printf "%s [WRN] Reservation for instance type %s already in state %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" $INSTANCE_TYPE "${state}"
    exit 0
  fi
done

#
# Issue a capacity request (1 hour validity) every 5 seconds until accepted
#
printf "%s [INF] Issuing capacity reservation request...\n" "$(date '+%Y-%m-%d %H:%M:%S')"
message_count=0
while true
do
  # calculate end time (1 hour from now) and issue reservation
  end_sec=$(((`date +%s`) + 3600))
  end_date=`date -u -Iseconds --date="@${end_sec}"`
  reservation=`aws ec2 --region $REGION create-capacity-reservation --end-date $end_date --end-date-type limited --instance-type $INSTANCE_TYPE --instance-platform Linux/UNIX --availability-zone $AVAILABILITY_ZONE --instance-count 1 2>&1`
  if [ $? -eq 0 ]
  then
    break
  fi

  # write message ~ every 5 minutes
  message_count=$(( $message_count - 1))
  if [ $message_count -le 0 ]
  then
    printf "%s [ERR] Capacity reservation failed: %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${reservation}"
    message_count=60
  fi
  sleep 5s
done


#
# Wait for capacity request to become active
#
printf "%s [INF] Waiting for active state...\n" "$(date '+%Y-%m-%d %H:%M:%S')"

states=`aws ec2 describe-capacity-reservations --filters "Name=instance-type,Values=${INSTANCE_TYPE}" --query CapacityReservations[].State | jq -r '.[]'`

for state in $states
do
  if [ $state == "active" ]
  then
    exit 0
  elif [ $state != "pending" ]
  then
    printf "%s [ERR] Capacity request has unexpected state %s.\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${state}"
    exit 8
  fi
  sleep 1m
done

printf "%s [INF] Reservation request is active now.\n" "$(date '+%Y-%m-%d %H:%M:%S')"

exit 0
