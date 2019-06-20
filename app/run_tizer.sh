#!/bin/bash

# copy kakadu apps from S3
aws s3 cp $KAKADU_APPS_LOCATION /kdu-apps.tar.gz

# unpack in place
cd / && tar -xzvf /kdu-apps.tar.gz

if [ -n "$AWS_ROUTE53_HOSTNAME" ]; then
  # get the container host's IP
  echo "Getting container host IP..."

  export LOCALIP=$(curl http://169.254.169.254/latest/meta-data/local-ipv4 2> /dev/null)

  echo "Container host IP is $LOCALIP"

  # upsert a DNS record for the IP using the name we have been given in the specified hosted zone
  cat > /tmp/route53-record.txt <<EOFCAT
{
  "Comment": "A new record set for the zone.",
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "$AWS_ROUTE53_HOSTNAME",
        "Type": "A",
        "TTL": 60,
        "ResourceRecords": [
          {
            "Value": "$LOCALIP"
          }
        ]
      }
    }
  ]
}
EOFCAT

  echo "Updating Route53, mapping $AWS_ROUTE53_ZONE_ID/$AWS_ROUTE53_HOSTNAME to $LOCALIP..."

  aws route53 change-resource-record-sets --hosted-zone-id $AWS_ROUTE53_ZONE_ID \
    --change-batch file:///tmp/route53-record.txt --region $AWS_REGION
fi

# bounce nginx
service nginx restart

# back to working directory and start uwsgi
cd /opt/tizer && uwsgi --ini /opt/tizer/tizer.ini

