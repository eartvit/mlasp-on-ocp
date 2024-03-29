#!/bin/bash

NOW=`date +%s`
ASYNCRESP="True"

ERR_COUNT=0

for (( i=0; i<$RUNS; ++i)); do

    ASYNC=$(($RANDOM%2))
    if [[ $ASYNC -eq 1 ]]
    then
      ASYNCRESP="True"
    else
      ASYNCRESP="False"
    fi
    
    TIMEOUT=$(($RANDOM % 5 + 1))

    echo -e 'Running cycle '$(($i+1))' out of '$RUNS' using async resp mode: '${ASYNCRESP}' and timeout: '${TIMEOUT}

    # with showlog the tkn command will stay until the pipeline executes
    #`tkn pipeline start auto-multipod-lt-wiremock --showlog --param connectionsLowerBound=10 --param connectionsUpperBound=30 --param durationLowerBound=10 --param durationUpperBound=60 --param scaleLowerBound=1 --param scaleUpperBound=15 --param timeout=5s --param outFormat=json --param URL=http://quarkus-metered-1-demo1.apps-crc.testing/data/250/30000 >> tkn_lt_pipeline_$NOW.log 2>&1`
    # without the showlog param, the tkn command will finish and then we need to monitor in a loop when the execution finished
    `tkn pipeline start auto-multipod-lt-wiremock --param cpuLimit=1 --param cpuRequest=500m --param memoryLimit=2Gi \
         --param memoryRequest=1Gi --param connectionsLowerBound=10 --param connectionsUpperBound=30 --param durationLowerBound=60 \
         --param durationUpperBound=600 --param scaleLowerBound=1 --param scaleUpperBound=15 --param timeout=${TIMEOUT}s \
         --param outFormat=json --param URL=http://wiremock-mlasp.demo1.svc.cluster.local:8080/another_mock --param asyncResp=${ASYNCRESP} \
         --param asyncRespThreadsLowerBound=10 --param asyncRespThreadsUpperBound=25 --param jacptQSizeLowerBound=1000 \
         --param jacptQSizeUpperBound=2000 --param jacptThreadsLowerBound=100 \
         --param jacptThreadsUpperBound=200 >> tkn_lt_pipeline_$NOW.log 2>&1`

    PIPELINERUN=`tkn pipelineruns list --no-headers | sed -n 1p | awk '{print $1}'`
    STATUS=`tkn pipelineruns list --no-headers | sed -n 1p | awk '{print $NF}'`
    while [[ $STATUS != 'Succeeded' ]]
    do
      echo -e 'Pipeline run '$PIPELINERUN' is '$STATUS'...'
      if [[ $STATUS == 'Failed' ]]; then
        echo -e 'Cleaning up resources of failed pipelinerun...'
        oc delete deployment,services -l app=wiremock-mlasp
        ERR_COUNT = $((ERR_COUNT+1))
        break;
      fi
      STATUS=`tkn pipelineruns list --no-headers | sed -n 1p | awk '{print $NF}'`
      sleep 5
    done
    if [[ $STATUS != 'Failed' ]]; then
      echo -e 'Pipeline run '$PIPELINERUN' is '$STATUS'.'
    fi
    echo -e 'Sleeping 60s before the next round starts.\n'
    sleep 60
done

if [[ $ERR_COUNT -gt 0 ]]; then
  echo -e 'Errors encountered: $ERR_COUNT'
fi


