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
COPY . .

# setup command
ENTRYPOINT ["./main.sh"]
EXPOSE 4983
