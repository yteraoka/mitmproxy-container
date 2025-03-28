"""
This script serializes the entire traffic dump, including websocket traffic,
as JSON, and either sends it to a URL or writes to a file. The serialization
format is optimized for Elasticsearch; the script can be used to send all
captured traffic to Elasticsearch directly.

Usage:

    mitmproxy
        --mode reverse:http://example.com/
        -s examples/complex/jsondump.py

Configuration:

    Send to a URL:

        cat > ~/.mitmproxy/config.yaml <<EOF
        dump_destination: "https://elastic.search.local/my-index/my-type"
        # Optional Basic auth:
        dump_username: "never-gonna-give-you-up"
        dump_password: "never-gonna-let-you-down"
        # Optional base64 encoding of content fields
        # to store as binary fields in Elasticsearch:
        dump_encodecontent: true
        EOF

    Dump to a local file:

        cat > ~/.mitmproxy/config.yaml <<EOF
        dump_destination: "/user/rastley/output.log"
        EOF
"""

import base64
import json
import logging
import re
from queue import Queue
from threading import Lock
from threading import Thread

import requests

from mitmproxy import ctx, http

FILE_WORKERS = 1
HTTP_WORKERS = 10


class JSONDumper:
    """
    JSONDumper performs JSON serialization and some extra processing
    for out-of-the-box Elasticsearch support, and then either writes
    the result to a file or sends it to a URL.
    """

    def __init__(self):
        self.transformations = None
        self.queue = Queue()

    def done(self):
        self.queue.join()

    fields = {
        "timestamp": (
            ("error", "timestamp"),
            ("request", "timestamp_start"),
            ("request", "timestamp_end"),
            ("response", "timestamp_start"),
            ("response", "timestamp_end"),
            ("client_conn", "timestamp_start"),
            ("client_conn", "timestamp_end"),
            ("client_conn", "timestamp_tls_setup"),
            ("server_conn", "timestamp_start"),
            ("server_conn", "timestamp_end"),
            ("server_conn", "timestamp_tls_setup"),
            ("server_conn", "timestamp_tcp_setup"),
        ),
        "ip": (
            ("server_conn", "source_address"),
            ("server_conn", "ip_address"),
            ("server_conn", "address"),
            ("client_conn", "address"),
        ),
        "ws_messages": (("messages",),),
        "headers": (
            ("request", "headers"),
            ("response", "headers"),
        ),
    }

    def _init_transformations(self):
        self.transformations = [
            {
                "fields": self.fields["headers"],
                "func": dict,
            },
            {
                "fields": self.fields["timestamp"],
                "func": lambda t: int(t * 1000),
            },
            {
                "fields": self.fields["ip"],
                "func": lambda addr: {
                    "host": addr[0].replace("::ffff:", ""),
                    "port": addr[1],
                },
            },
            {
                "fields": self.fields["ws_messages"],
                "func": lambda ms: [
                    {
                        "type": m[0],
                        "from_client": m[1],
                        "timestamp": int(m[3] * 1000),
                    }
                    for m in ms
                ],
            },
        ]


    @staticmethod
    def transform_field(obj, path, func):
        """
        Apply a transformation function `func` to a value
        under the specified `path` in the `obj` dictionary.
        """
        for key in path[:-1]:
            if not (key in obj and obj[key]):
                return
            obj = obj[key]
        if path[-1] in obj and obj[path[-1]]:
            obj[path[-1]] = func(obj[path[-1]])

    @classmethod
    def convert_to_strings(cls, obj):
        """
        Recursively convert all list/dict elements of type `bytes` into strings.
        """
        if isinstance(obj, dict):
            return {
                cls.convert_to_strings(key): cls.convert_to_strings(value)
                for key, value in obj.items()
            }
        elif isinstance(obj, list) or isinstance(obj, tuple):
            return [cls.convert_to_strings(element) for element in obj]
        elif isinstance(obj, bytes):
            return str(obj)[2:-1]
        return obj

    def worker(self):
        while True:
            frame = self.queue.get()
            self.dump(frame)
            self.queue.task_done()

    def dump(self, frame):
        """
        Transform and dump (write / send) a data frame.
        """
        for tfm in self.transformations:
            for field in tfm["fields"]:
                self.transform_field(frame, field, tfm["func"])
        frame = self.convert_to_strings(frame)

        if 'certificate_list' in frame['server_conn']:
            del frame['server_conn']['certificate_list']

        #del frame['request']['content']
        #del frame['response']['content']

        print(json.dumps(frame))

    def configure(self, _):
        """
        Determine the destination type and path, initialize the output
        transformation rules.
        """
        self._init_transformations()

        t = Thread(target=self.worker)
        t.daemon = True
        t.start()

    def response(self, flow):
        """
        Dump request/response pairs.
        """
        self.queue.put(flow.get_state())

    def error(self, flow):
        """
        Dump errors.
        """
        self.queue.put(flow.get_state())

    def websocket_end(self, flow):
        """
        Dump websocket messages once the connection ends.

        Alternatively, you can replace `websocket_end` with
        `websocket_message` if you want the messages to be
        dumped one at a time with full metadata. Warning:
        this takes up _a lot_ of space.
        """
        self.queue.put(flow.get_state())


addons = [JSONDumper()]  # pylint: disable=invalid-name
