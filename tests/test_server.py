
import os
import pytest
import unittest
import random
import socket
import time
import webbrowser

from progress.server import ProgressServer


class TestProgressServer(unittest.TestCase):
    def test_start_stop(self):
        server = ProgressServer(open_browser=None)
        server.start()
        server.wait_until_ready()
        port = server.port
        connection = socket.create_connection(("localhost", port), timeout=1)
        connection.send(b"GET / HTTP/1.1\r\n\r\n")
        data = connection.recv(1024)
        self.assertIsNotNone(data)
        self.assertIn(b"200 OK", data)
        server.stop()
    
    def test_event_stream(self):
        server = ProgressServer(open_browser=None)
        server.start()
        server.wait_until_ready()
        port = server.port
        connection = socket.create_connection(("localhost", port), timeout=1)
        connection.send(b"GET /events HTTP/1.1\r\n\r\n")
        server.add_event("test")
        time.sleep(0.1)  # if too fast, the event won't propagate in time
        # Make sure we get past all the headers.
        data = connection.recv(2048)
        self.assertIn(b"data: test\n\n", data)
        server.stop()
        data = connection.recv(1024)
        self.assertIn(b"event: abort\ndata: {\"reason\": \"shutdown\"}\n\n", data)
    
    def test_custom_resource(self):
        data = b"<html><body>Success</body></html>"
        resources = {"/test": data}
        server = ProgressServer(open_browser=None, web_resources=resources)
        server.start()
        server.wait_until_ready()
        port = server.port
        connection = socket.create_connection(("localhost", port), timeout=1)
        connection.send(b"GET /test HTTP/1.1\r\n\r\n")
        received = connection.recv(1024)
        self.assertIn(data, received)

    @pytest.mark.manual
    def test_manual(self):
        server = ProgressServer(open_browser=1)
        server.start()
        self.assertEqual(1, server.wait_until_ready(timeout=2))
        server.add_event("Data")
        counter = 0
        while counter < 20:
            time.sleep(1)
            counter += 1
            server.add_event(f"count {counter}")
        server.stop()
