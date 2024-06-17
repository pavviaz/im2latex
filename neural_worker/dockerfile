FROM python:3.11

RUN apt-get update && apt-get install libgl1 ffmpeg -y

WORKDIR /neural_worker

COPY requirements.txt /neural_worker/
RUN pip install -r requirements.txt
COPY . /neural_worker/