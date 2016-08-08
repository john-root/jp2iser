from boto import sqs
from boto.sqs.message import Message
import qtizer_settings as settings

d2 = """{
  "_type": "event",
  "_created": "2016-04-19T13:08:35.7575355+00:00",
  "message": "event::image-ingest-more",
  "params": {
    "source": "/Users/Giskard/tizerstuff/barley.jpg",
    "jobid": "123",
    "thumbSizes": "[1000,400,100]",
    "destination": "/Users/Giskard/tizerstuff/barley.jp2",
    "thumbDir": "/Users/Giskard/tizerstuff"
  }
}"""

conn = sqs.connect_to_region(settings.SQS_REGION)
queue = conn.get_queue(settings.INPUT_QUEUE)

m2 = Message()
m2.set_body(d2)
queue.write(m2)
