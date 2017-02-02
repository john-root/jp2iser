FROM ubuntu

ENV KAKADU_APPS_LOCATION s3://dlcs-bootstrap-objects/kdu77-apps.tar.gz

RUN apt-get update -y && apt-get install -y python-pip python-dev build-essential nginx uwsgi
COPY app /opt/tizer
COPY etc/tizer.nginx.conf /etc/nginx/sites-available/tizer
RUN ln -s /etc/nginx/sites-available/tizer /etc/nginx/sites-enabled/tizer && rm -f /etc/nginx/sites-enabled/default
RUN pip install -r /opt/tizer/requirements.txt
RUN mkdir /opt/tizer/tmp
WORKDIR /opt/tizer
CMD /opt/tizer/run_tizer.sh
EXPOSE 80
