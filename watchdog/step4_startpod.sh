#! /bin/bash

source ./.env

replicas=`oc get deployments -n $NAMESPACE -o jsonpath="{.items[?(@.metadata.name==\"${INFERENCE_SERVER_POD}\")].status.replicas}"`

if [ -z $replicas ] || [ $replicas -lt 1 ]
then
  printf "%s [INF] Starting pod for deployment %s...\n" "$(date)" $INFERENCE_SERVER_POD
  scaleup=`oc scale --replicas=1 deployment "${INFERENCE_SERVER_POD}" -n $NAMESPACE 2>&1`
  printf "%s [INF] %s\n" "$(date)" "${scaleup}"
  if [ $? -ne 0 ]
  then
     printf "%s [ERR] Upscaling deployment %s failed.\n" "$(date)" $INFERENCE_SERVER_POD
  fi
fi

printf "%s [INF] Waiting for replica of %s to become ready...\n" "$(date)" $INFERENCE_SERVER_POD
while true
do
  readyReplicas=`oc get deployments -n $NAMESPACE -o jsonpath="{.items[?(@.metadata.name==\"${INFERENCE_SERVER_POD}\")].status.readyReplicas}"`
  if [ ! -z $readyReplicas ]
  then
    if [ $readyReplicas -ge 1 ]
    then
      break
    fi
  fi
  sleep 5s
done

replicasets=(`oc get replicaset -n $NAMESPACE -o jsonpath="{range .items[?(@.metadata.ownerReferences[].name==\"${INFERENCE_SERVER_POD}\")]}[\"{.metadata.name}\",\"{.metadata.creationTimestamp}\"] {end}" | jq -r "flatten[]"`)
latest="0"
for (( i=0; i<${#replicasets[@]}; i+=2 ))
do
  creationTimestamp=${replicasets[(( $i + 1 ))]}
  if [ $creationTimestamp > $latest ]
  then
    replicaset=${replicasets[$i]}
    latest=$creationTimestamp
  fi
done

printf "%s [INF] ReplicaSet %s is latest.\n" "$(date)" $replicaset
for rs in $replicasets
do
  if [ $rs != $replicaset ]
  then
    printf "%s [WRN] Deleting replicaSet %s...\n" "$(date)" $rs
    rsdel=`oc delete replicaset $rs -n $NAMESPACE 2>&1`
    printf "%s [INF] %s\n" "$(date)" "${rsdel}"
  fi
done

pod=`oc get pod -n $NAMESPACE -o jsonpath="{.items[?(@.metadata.ownerReferences[].name==\"${replicaset}\")].metadata.name}"`

printf "%s [INF] Waiting for pod %s to get ready...\n" "$(date)" $pod

while true
do
  status=(`oc get pod $pod -n $NAMESPACE -o jsonpath="{ range .status.conditions[*]}[\"{.status}\"]{end}" | jq -r "flatten[]"`)
  if [ ${#status} -ge 4 ]
  then
    break
  fi
done

printf "%s [INF] Pod %s up and running, checking log...\n" "$(date)" $pod

while true
do
  unset serverStarted
  oc logs $pod -n $NAMESPACE |
    while read -r line
    do
      if [[ $line == *"server started"* ]]
      then
        printf "%s [INF] Found in log: "%s"\n" "$(date)" "${line}"
        serverStarted=true
      fi
    done

  echo $serverStarted

  if $serverStarted
  then
    break
  fi
  sleep 10s
done

printf "%s [INF] Pod %s ready to serve requests.\n" "$(date)" $pod


