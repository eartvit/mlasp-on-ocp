# FROM python:3.7-slim
FROM registry.access.redhat.com/ubi8/python-38
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt


# Define environment variable
ENV MODEL_NAME TestXGB
ENV SERVICE_TYPE MODEL
ENV ENV_MODEL_NAME TestXGB
ENV ENV_PREDICTOR_NAME = BNE


CMD exec seldon-core-microservice $MODEL_NAME --service-type $SERVICE_TYPE --http-port 8080
