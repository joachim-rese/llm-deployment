#!/bin/bash

source ./.env

printf "%s [INF] Checking connection to cluster...\n" "$(date '+%Y-%m-%d %H:%M:%S')"
server=`oc whoami --show-server`
if [ $server != $OCP_API_URL ]
then
  printf "%s [WRN] Wrong server %s (expecting %s)... performing logout\n" "$(date '+%Y-%m-%d %H:%M:%S')" $server $OCP_API_URL
  oc logout
fi


#
# Login to cluster, get new token, if necessary
#
user=`oc whoami 2>&1`
words=`echo $user | wc -w`

if [ $words -gt 1 ]
then
  printf "%s [INF] Login...\n" "$(date '+%Y-%m-%d %H:%M:%S')"
  token=`curl -u $OCP_USER:$OCP_PASSWORD -H "X-CSRF-Token: xxx" "${OCP_AUTH_URL}/oauth/authorize?client_id=openshift-challenging-client&response_type=token" -kL -w %{url_effective} | grep -oP "access_token=\K[^&]*"`
  printf "%s [INF] Got Token %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${token}"
  login=`oc login --token=$token --server=$OCP_API_URL 2>&1`
  if [ $? -ne 0 ]
  then
    printf "%s [ERR] oc login failed: %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${login}"
    exit 8
  fi
  printf "%s [INF] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${login}"
else
  printf "%s [INF] Logged in as %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${user}"
fi


#
# Scale up relevant machine set, if necessary
#
zones=(`aws ec2 describe-capacity-reservations --filters "[{\"Name\": \"instance-type\", \"Values\": [\"${INSTANCE_TYPE}\"]}, {\"Name\": \"state\", \"Values\": [\"active\"]}]" --query CapacityReservations[].AvailabilityZone | jq -r 'flatten[]'`)

if [ ${#zones[@]} -lt 1 ]
then
  azone="${AVAILABILITY_ZONE}"
else
  azone=${zones[0]}
fi

msets=(`oc get machineset -n openshift-machine-api -o jsonpath="{range .items[?(@.spec.template.spec.providerSpec.value.placement.availabilityZone==\"${azone}\")]}[\"{.metadata.name}\",\"{.spec.template.spec.providerSpec.value.instanceType}\",\"{.status.replicas}\"] {end}" | jq -r "flatten[]"`)

unset $msetId
for (( i=0; i<${#msets[@]}; i+=3 ))
do
  instanceType=${msets[(( $i + 1 ))]}
  if [ $instanceType == $INSTANCE_TYPE ]
  then
    msetId=${msets[$i]}
    replicas=${msets[(( $i + 2 ))]}
    printf "%s [INF] Machine Set (instance type: %s, availability zone: %s, replicas: %s) found: %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${instanceType}" "${azone}" "${replicas}" "${msetId}"
    break
  fi
done

if [ -z $msetId ]
then
  printf "%s [ERR] Machine Set (instance type: %s, availability zone: %s) not found\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${INSTANCE_TYPE}" "${azone}"
  exit 8
fi

if [ $replicas -eq 0 ]
then
  printf "%s [INF] Increasing number of machines in machine set %s...\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${msetId}"
  scaleup=`oc scale --replicas=1 machineset "${msetId}" -n openshift-machine-api 2>&1`
  printf "%s [INF] %s\n" "$(date)" "${scaleup}"
  if [ $? -ne 0 ]
  then
     printf "%s [ERR] Upscaling machine set %s failed.\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${INSTANCE_TYPE}" "${msetId}"
  fi
fi


#
# Wait for machine to become ready
#
printf "%s [INF] Waiting for machine in machine set %s to become ready...\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${msetId}"
while true
do
   readyReplicas=`oc get machineset sap-dat5-4hrkd-worker-us-west-2b -n openshift-machine-api -o jsonpath="{.status.readyReplicas}"`
   if [[ -n $readyReplicas || $readyReplicas -gt 0 ]]
   then
     break
   fi
   sleep 10s
done

machines=`(oc get machine -n openshift-machine-api -o jsonpath="{.items[?(@.metadata.ownerReferences[].name==\"${msetId}\")].metadata.name}")`
unset $machine
while true
do
  for mach in $machines
  do
    phase=`oc get machine $mach -n openshift-machine-api -o jsonpath="{.status.phase}"`
    if [ ! -z $phase ] && [ $phase == "Running" ]
    then
      machine="${mach}"
      break
    fi
  done
  
  if [ -z $machine ]
  then
    printf "%s [INF] Machine set %s ready, but no machine found yet.\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${msetId}"
    sleep 10s
  else
    break
  fi
done


#
# Wait for node to become ready
#
printf "%s [INF] Waiting for machine %s to become node...\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${machine}"

unset node
while true
do
  nodes=(`oc get node -o jsonpath="{range .items[*]}[\"{.metadata.name}\",\"{.metadata.annotations.machine\.openshift\.io/machine}\"] {end}" | jq -r "flatten[]"`)
  for (( i=0; i<${#nodes[@]}; i+=2 ))
  do
    mach=${nodes[(( $i + 1 ))]}
    if [ $mach == "openshift-machine-api/${machine}" ]
    then
      node=${nodes[$i]}
      break
    fi
  done
  if [[ -n $node ]]
  then
    break
  fi
  sleep 5s
done
  

printf "%s [INF] Waiting for node %s to become ready...\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${node}"

while true
do
  status=`oc get node $node -o jsonpath="{.status.conditions[?(@.type==\"Ready\")].status}"`
  if [[ -n $status && $status=="True" ]]
  then
    break
  fi
  sleep 5s
done

printf "%s [INF] Node %s is ready now.\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${node}"



