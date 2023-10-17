#!/bin/bash

source ./.env

set_availaibilty_zone() {
  active_reqs=(`aws ec2 describe-capacity-reservations --filters "[{\"Name\": \"instance-type\", \"Values\": [\"${INSTANCE_TYPE}\"]}, {\"Name\": \"state\", \"Values\": [\"${1}\"]}]" --query CapacityReservations[].AvailabilityZone | jq -r '.[]'`)
  if [[ ${#active_reqs} -eq 0 ]]
  then
    printf "%s [ERR] Cannot determine availability zone of %s Capacity Reservation\n" "$(date '+%Y-%m-%d %H:%M:%S')" $1
    exit 8
  else
    azone=${active_reqs[0]}
    if [ -z $AVAILABILITY_ZONE ]
    then
      if [[ $(tail -c1 .env | wc -l) -eq 0 ]]
      then
        newline='\n'
      fi
      echo -e "${newline}AVAILABILITY_ZONE=${azone}" >> .env
    else
      sed -i "/AVAILABILITY_ZONE=/s/=.*$/=${azone}/" .env
    fi
  fi
}


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
    printf "%s [WRN] Reservation for instance type %s already in state \"%s\"\n" "$(date '+%Y-%m-%d %H:%M:%S')" $INSTANCE_TYPE "${state}"
    set_availaibilty_zone $state
    exit 0
  fi
done


#
# Issue a capacity request (1 hour validity) every 5 seconds until accepted
#
printf "%s [INF] Issuing capacity reservation request for zones %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${AVAILABILITY_ZONE_LIST}"
readarray -d ',' -t azones < <(printf %s "${AVAILABILITY_ZONE_LIST//[$'\t\r\n']/}")

message_count=0
while true
do
  message_count=$(( $message_count - 1))
  # calculate end time (1 hour from now) and issue reservation
  end_sec=$(((`date +%s`) + 3600))
  end_date=`date -u -Iseconds --date="@${end_sec}"`
  for azone in ${azones[@]}
  do
    reservation=`aws ec2 create-capacity-reservation --region $REGION --availability-zone $azone --end-date $end_date --end-date-type limited --instance-type $INSTANCE_TYPE --instance-platform Linux/UNIX --instance-count 1 2>&1`
    if [ $? -eq 0 ]
    then
      break
    fi

    # write message ~ every 5 minutes
    if [ $message_count -le 0 ]
    then
      printf "%s [ERR] Capacity reservation failed (zone %s): %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${azone}" "${reservation}"
    fi
  done
  if [ $message_count -le 0 ]
  then
    message_count=$(( 300 / ( 5 * ( ${#azones[@]} + 1 ) ) ))
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
    set_availaibilty_zone $state
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
