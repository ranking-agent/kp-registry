FROM python:3.9.1-buster

# add Container Info
LABEL org.opencontainers.image.source https://github.com/ranking-agent/kp_registry

# mkdir
RUN mkdir /app

# install requirements
ADD ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# install server
ADD ./kp_registry /app/kp_registry
ADD ./main.sh /app/main.sh

# setup command
RUN mkdir /app/data
WORKDIR /app
CMD ["/app/main.sh"]
EXPOSE 4983
