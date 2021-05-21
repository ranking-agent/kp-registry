FROM python:3.9.1-buster

# add Container Info
LABEL org.opencontainers.image.source https://github.com/ranking-agent/kp_registry

# mkdir
RUN mkdir /app
WORKDIR /app

# install requirements
ADD ./requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# install server
ADD ./kp_registry ./kp_registry
ADD ./main.sh ./main.sh

# setup command
RUN mkdir data
ENTRYPOINT ["./main.sh"]
EXPOSE 4983
