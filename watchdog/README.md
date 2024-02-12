# Full Automated Test

To implement full automated testing, proceed as follows:

Clone this subdirectory and 'cd' into your local copy.

Create file **.env** holding the following content. (Copy file .env_template initially.)

|Variable|Value|
|:---|:---|
|REGION|Region of GPU instance|
|AVAILABILITY_ZONE_LIST|List of possible availability zones for reservation|
|INSTANCE_TYPE|AWS Instance Type, for example<br>p3.8xlarge (V100)<br>p4d.24xlarge (A100, 40GB x 8)<br>p4de.24xlarge (A100, 80GB x 8)<br>p5.48xlarge (H100, 80GB x 8)|
|INFERENCE_SERVER_POD|Inference server deployment, for exmaple llama-2-13b-chat-inference-server|
|NAMESPACE|Project name of fmaas stack|
|TESTTOOL_APP<br>TESTTOOL_WORKDIR<br>TESTTOOL_VENV|Executable, work directory and python virtual environment of test tool|
|OCP_CLUSTER<br>OCP_USER<br>OCP_PASSWORD|OpenShift cluster, user and password|
|OCP_AUTH_URL<br>OCP_API_URL|OpenShift cluster oauth and api endpoint|
|SHUTDOWN|Flag whether cluster is shutdown after test and on error (true/false/auto). auto = Cluster is shutdown if and only if it has been started by this tooling.|

Afterwards start automated test in background
```
nohup ./run.sh [steps] > run.out &
```

All scripts with prefix *stepX* will be executed in alphabetical order, where X is in *steps*. For example
```
nohup ./run.sh 134 > run.out &
```
runs all scripts starting with step1, step3 or step4.


The provided scripts perform these tasks:

|Script|Tasks|
|:---|:---|
|`step1_reservation.sh`|* Issue a capacity request (1 hour validity) every 5 seconds until accepted<br>* Wait for capacity request to become active|
|`step2_startup.sh`|* Start cluster<br>* Wait until all instances have finished initialization|
|`step3_setup.sh`|* Login to cluster, get new token, if necessary<br>* Scale up relevant machine set, if necessary<br>* Wait for machine to become ready<br>* Wait for node to become ready|
|`step4_startpod.sh`|* Upscale deployment, if necessary<br>* Delete obsolete replicaSets<br>* Wait for pod to become ready<br>* Wait for inference server to become ready (check logs)|
|`step5_experiment.sh`|* Run test tool|
|`step6_shutdown.sh`|* Shutdown cluster (stop all cluster instances)

