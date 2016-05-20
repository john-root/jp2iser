from multiprocessing import Pool
import qtizer_settings as settings
from boto import sqs
from boto.sqs.message import Message
import json
import requests
import pytz
import datetime
import logging
import base64

output_queue = None
logger = None


def main():
    input_queue = get_input_queue()

    logging.basicConfig(
                        filename=settings.log_file,
                        level=getattr(logging, settings.log_level))


    # TODO : check queues not None

    pool = Pool(5, initializer=init_pool, initargs=())

    try:
        while True:
            messages = input_queue.get_messages(num_messages=10, visibility_timeout=120, wait_time_seconds=20)
            if len(messages) > 0:
                pool.map(process_message, messages)
    except:
        logging.exception("Error getting messages")


def process_message(message):
    try:
        message_payload = json.loads(str(message.get_body()))

        # payload may be encoded in standard message format
        if '_type' in message_payload and 'message' in message_payload \
                and message_payload['message'] == "event::call-tizer":
            message_payload = convert_input_message_format(message_payload)

        call_tizer(message_payload)

    except Exception as e:
        print e

    message.delete()


def call_tizer(payload):

    r = requests.post(settings.TIZER_SERVICE, json=payload)
    if r.status_code == 200:
        message = {
            '_type': 'event',
            '_created': str(datetime.datetime.now(pytz.timezone('UTC'))),
            'message': 'event::tizer-output',
            'params': r.json(),

        }
        message = convert_output_message_format(message)
        send_message(json.dumps(message))
    # TODO : log


def send_message(payload):

    msg = Message()
    msg.set_body(payload)
    output_queue.write(msg)


def convert_input_message_format(message_payload):

    if 'params' in message_payload:
        message_payload = message_payload['params']
        if 'thumbSizes' in message_payload:
            message_payload['thumbSizes'] = map(int, message_payload['thumbSizes'][1: -1].split(','))
            return message_payload
    return None


def convert_output_message_format(message_payload):

    if 'params' in message_payload and 'thumbs' in message_payload['params']:
        thumbs = message_payload['params']['thumbs']
        string_thumbs = json.dumps(thumbs)
        encoded_thumbs = base64.b64encode(string_thumbs.encode('utf-8'))
        message_payload['params']['thumbs'] = encoded_thumbs
    return message_payload


def init_pool():
    global output_queue
    output_queue = get_output_queue()


def get_input_queue():
    conn = sqs.connect_to_region(settings.SQS_REGION)
    queue = conn.get_queue(settings.INPUT_QUEUE)
    return queue


def get_output_queue():
    conn = sqs.connect_to_region(settings.SQS_REGION)
    queue = conn.get_queue(settings.OUTPUT_QUEUE)
    return queue


if __name__ == "__main__":
    main()



