FROM python:3.8.1-buster

# Add Container Info
LABEL org.opencontainers.image.source https://github.com/ranking-agent/kp_registry

# install basic tools
RUN apt-get update
RUN apt-get install -yq \
    vim

# set up murphy
RUN mkdir /home/murphy
ENV HOME=/home/murphy
ENV USER=murphy
WORKDIR /home/murphy

# install requirements
ADD ./requirements.txt /home/murphy/requirements.txt
RUN pip install -r /home/murphy/requirements.txt --src /usr/local/src

# install server
ADD ./kp_registry /home/murphy/kp_registry
ADD ./main.sh /home/murphy/main.sh

# setup command
CMD ["/home/murphy/main.sh"]
EXPOSE 4983
