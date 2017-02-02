#!/bin/bash

aws s3 cp $KAKADU_APPS_LOCATION /kdu-apps.tar.gz

cd / && tar -xzvf /kdu-apps.tar.gz

service nginx restart

cd /opt/tizer && uwsgi --ini /opt/tizer/tizer.ini

