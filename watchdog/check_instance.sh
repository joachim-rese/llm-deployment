#!/bin/bash

source ./.env

states=`aws ec2 describe-instances --filters "Name=instance-type,Values=$INSTANCE_TYPE" --query "Reservations[].Instances[].State.Code" | jq -c '.[]'`

running=false
for state in $states
do
  if [ $state == '16' ]
  then
    exit 0
  fi
done

exit 8
