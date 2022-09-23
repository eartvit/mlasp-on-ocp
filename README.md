# Machine Learning Assisted System Performance and Capacity Planning (MLASP) on Red Hat OpenShift
This is a demo for the overall process described in the MLASP research paper published at Springer EMSE on the Red Hat Openshift platform.
* DOI: https://link.springer.com/article/10.1007/s10664-021-09994-0
* Link to the article: https://rdcu.be/cobcU

In order to execute the below guide, access to a Red Hat OpenShift environment is required. If you don't have one, you can start a trial by creating an account at https://cloud.redhat.com. Alternatively, it is also possible to execute the guide on a local (reduced version) of the platform, typically used for development purposes. Once you registered on the https://cloud.redhat.com, you can obtain your version of the local Red Hat Openshift by downloading the installer from the [Console](https://console.redhat.com/openshift/create/local).

## Foreword
This repository presents a step by step guide on a possible setup of the MLASP process described in the before mentioned research article published by Springer's Empirical Sofware Engineering Journal.

The aim of this guide is to show a general approach to implementing the MLASP process described in the research paper on the RedHat OpenShift platform. Given the general form of the process, there may be different ways, meaning using different tools, to implement the different areas of the process.

The guide in this repository does not recreate the open-source system used in the initial research (which is published in the @SPEAR-SE organization: https://github.com/SPEAR-SE/mlasp.

For convenience, the overall MLASP process diagram is presented below:
![mlasp-process](images/mlasp-process.png)

## What is Red Hat OpenShift
Red Hat OpenShift is a leading enterprise Kubernetes platform1 that enables a cloud-like experience everywhere it's deployed. Whether it’s in the cloud, on-premise or at the edge, Red Hat OpenShift gives you the ability to choose where you build, deploy, and run applications through a consistent experience (Source: https://www.redhat.com/en/technologies/cloud-computing/openshift).

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

## Automated Load Testing
One way to achieve automation inside RedHat Openshift is with the help of [Tekton](https://tekton.dev/) pipelines. Tekton is available as an operator inside OpenShift and may be installed globally on the cluster from within the Operator Hub where they are called ***RedHat OpenShift Pipelines***
![openshift-pipelines-operator-hub](images/rh-ocp-pipelines-01.png)

Tekton is a Kubernetes native implementation of CI/CD systems which in our case we shall use to automate the load testing of a subject system for activities such as:
* generate load test parameters for the controlled load generator application.
* generate configuration parameters for the subject test system (including number of instances).
* deploy the subject test system using the generated parameter configuration for the load test.
* extract (in a non-intrusive way) and store load test results into a timeseries database (used later on as input for the ML modelling).
* perform cleanup after a load test





