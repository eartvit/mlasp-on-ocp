# FROM python:3.7-slim
FROM registry.access.redhat.com/ubi8/python-38
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt


# Define environment variable
ENV SERVICE_PORT 8080


CMD exec python test-app.py
