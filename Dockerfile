FROM renciorg/renci-python-image:v0.0.1

# add Container Info
LABEL org.opencontainers.image.source https://github.com/ranking-agent/kp_registry

# mkdir
RUN mkdir /app
WORKDIR /app

# make sure all is writeable for the nru USER later on
RUN chmod -R 777 .

# install requirements
ADD ./requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# switch to the non-root user (nru). defined in the base image
USER nru

# install server
COPY . .

# setup command
ENTRYPOINT ["./main.sh"]
EXPOSE 4983
