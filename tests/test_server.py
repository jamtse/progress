
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
        port = int(random.random()*1000) + 34567
        server = ProgressServer(port)
        server.start()
        connection = socket.create_connection(("localhost", port), timeout=1)
        data = connection.recv(1024)
        self.assertIsNotNone(data)
        self.assertIn(b"200 OK", data)
        server.stop()
    
    @pytest.mark.manual
    def test_manual(self):
        port = 12345
        webbrowser.open("file://" + os.path.realpath("serversidetest.html"), new = 1)
        server = ProgressServer(port)
        server.start()
        server.add_event("Data")
        counter = 0
        while counter < 100:
            time.sleep(1)
            counter += 1
            server.add_event(f"count {counter}")
        server.stop()
