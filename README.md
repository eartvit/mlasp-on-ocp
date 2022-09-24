# Machine Learning Assisted System Performance and Capacity Planning (MLASP) on Red Hat OpenShift

This is a demo for the overall process described in the MLASP research paper published at Springer EMSE on the Red Hat Openshift platform:

* [DOI](https://link.springer.com/article/10.1007/s10664-021-09994-0)
* Link to the [article](https://rdcu.be/cobcU)

In order to execute the below guide, access to a Red Hat OpenShift environment is required. If you don't have one, you can start a trial by creating an account at https://cloud.redhat.com. Alternatively, it is also possible to execute the guide on a local (reduced version) of the platform, typically used for development purposes. Once you registered on the https://cloud.redhat.com, you can obtain your version of the local Red Hat Openshift by downloading the installer from the [Console](https://console.redhat.com/openshift/create/local).

## Foreword

This repository presents a step by step guide on a possible setup of the MLASP process described in the before mentioned research article published by Springer's Empirical Sofware Engineering Journal.

The aim of this guide is to show a general approach to implementing the MLASP process described in the research paper on the RedHat OpenShift platform. Given the general form of the process, there may be different ways, meaning using different tools, to implement the different areas of the process.

The guide in this repository does not recreate the open-source system used in the initial research which is published in the [@SPEAR-SE](https://github.com/SPEAR-SE/mlasp) organization on GitHub.

For convenience, the overall MLASP process diagram is presented below:
![mlasp-process](images/mlasp-process.png)

## What is Red Hat OpenShift

[Red Hat OpenShift Container Platform](https://www.redhat.com/en/technologies/cloud-computing/openshift/container-platform) is a leading enterprise Kubernetes platform that enables a cloud-like experience everywhere it's deployed. Whether it’s in the cloud, on-premise or at the edge, Red Hat OpenShift gives you the ability to choose where you build, deploy, and run applications through a consistent experience (Source: [RedHat](https://www.redhat.com/en/technologies/cloud-computing/openshift)).

In other words, Red Hat OpenShift Container Platform is a private Platform as a Service (PaaS) for enterprises that run OpenShift on public clouds or on-premises infrastructure. The OpenShift platform is a consistent hybrid cloud foundation for building and scaling containerized applications. In other words, it is an open-source container orchestration platform for enterprises. It includes several container technologies, primarily the OpenShift container orchestration software, which is based on the OKD open-source project. Red Hat OpenShift combines Kubernetes components with security features and productivity necessary for large enterprises and is especially useful in hybrid cloud scenarios.

Red Hat OpenShift uses operators. [Operators](https://docs.openshift.com/container-platform/4.11/operators/understanding/olm-what-operators-are.html) are pieces of software that ease the operational complexity of running another piece of software.

Throughout this guide we shall use several operators for different purposes.

## Introduction and Overview

As seen in the above diagram, there are three major areas of the MLASP process:

* Automated Load Testing: for training data generation.
* Machine Learning Modelling and Training : for creating a model that may be used for predictions.
* ML Model Serving (Inferencing): for using the previously trained model to provide predictions for two scenarios:
  * What if scenario: where the model will provide a prediction based on specific inputs.
  * Find a configuration with a given (percentage) deviation from a desired target.

We shall address these areas in the next sections.
This guide assumes a full version of RedHat OpenShift is used. The steps for deploying on the developer version (local) are the same, however the local version will not provide insights on the system metrics (i.e. pod CPU usage, pod memory usage, etc.). For demonstration purposes, only application metrics shall be used for the ML modelling process, therefore the fact that an OpenShift Local instance does not provide these details are irrelevant for the demonstration.

Another assumption for the purposes of this demonstration is that the namespace (a.k.a. project space) inside OpenShift where all the applications will deployed is called ```demo1```.

## Automated Load Testing

One way to achieve automation inside RedHat Openshift is with the help of [Tekton](https://tekton.dev/) pipelines. Tekton is available as an operator inside OpenShift and may be installed globally on the cluster from within the Operator Hub where they are called ***RedHat OpenShift Pipelines***
![openshift-pipelines-operator-hub](images/rh-ocp-pipelines-01.png)

Tekton is a Kubernetes native implementation of CI/CD systems which in our case we shall use to automate the load testing of a subject system for activities such as:

* Generate load test parameters for the controlled load generator application.
* Generate configuration parameters for the subject test system (including number of instances).
* Deploy the subject test system using the generated parameter configuration for the load test.
* Extract (in a non-intrusive way) and store load test results into a timeseries database (used later on as input for the ML modelling).
* Perform cleanup after a load test.

A Tekton pipeline is formed from Tasks that may execute in parallel or in sequence, depending on the workflow definition of the pipeline. Remember, Tekton is a kubernetes native system which means every task lives inside it's own Kubernetes pod.

In this demonstration we use [bombardier](https://github.com/codesenberg/bombardier) as load generator. We can control several of its parameters to apply different load configurations over the test subject system, which is in our case a mock simulator, [Wiremock](https://wiremock.org/). We selected Wiremock for the test subject as it is a generic web server that may provide templated responses following a specified distribution for the response time, such as uniform distribution, which is typical for production systems. Following the details of the MLASP paper, we shall try to model the throughput of the wiremock application by altering some of its web server parameters. We shall apply load over differen wiremock configuration and measure the throughput which we then will later model inside the RedHat OpenShift Platform.

The tekton pipeline executing a load test has several different tasks as mentioned above. Tasks which generate parameter ranges such as how many threads the wiremock shall use to process incoming requests, tasks which control deployment, tasks which extract information and store it in a (timeseries) database, and task for cleanup.

A tekton pipeline may be created outside of the RedHat Openshift platform and then imported using the ```oc``` command. Additionally, a tekton pipeline may be created directly inside the OpenShift's web console, either by directly writing the yaml file for the pipeline, or using the graphical interface for linking the tasks. The visual representation of the pipeline makes it easy to understand what steps are executed in parallel or in sequence and at what stage. The earlier mentioned steps have been groupped together in a pipeline having the following visual representation:
![auto-multipod-lt-wiremock](images/auto-multipod-lt-wiremock-01.png)

For this demonstration purposes, the pipeline is provided as part of this repository. To import it into OpenShift, ensure you are in the correct namespace (i.e., demo1) and apply first the tasks' yaml definitions followed by the pipeline's yaml definition:

```bash
oc project demo1
oc apply -f task-generate-random-number.yaml
oc apply -f task-bombardier-task.yaml
oc apply -f task-scale-deployment-task.yaml
oc apply -f task-lt-summary.yaml
oc apply -f task-wiremock-cleanup.yaml
oc apply -f task-wiremock-deploy.yaml
oc apply -f task-calculate-cthreads-value-task.yaml
oc apply -f auto-multipod-lt-wiremock.yaml
```





