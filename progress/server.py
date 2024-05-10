import socket
import threading
import time


class ProgressServer(threading.Thread):
    """Server for displaying the progress of an application

    Spawn a thread that waits for a connection and then start serving
    server side events with context data.

    Only one connection is served at a time.

    Events are added on to a list that is never dropped, to allow
    re-connecting.
    """
    LB = b"\r\n"
    HEADER = LB.join([
        b"HTTP/1.1 200 OK",
        b"Server: ProgressServer",
        b"X-Accel-Buffering: no",
        b"Content-Type: text/event-stream",
        b"Cache-Control: no-cache",
        # null is for files opened dirctly in browser
        # TODO not sure if this is what I want, perhaps the page should be
        #  served from this sever as well..
        b"access-control-allow-origin: null",
    ])

    def __init__(self, port) -> None:
        self.running = False
        self.port = port
        self.adress = "localhost"
        self.__server_socket = None
        self.events = []
        self.pos = 0
        self.update_event = threading.Event()
        super().__init__()
    
    def run(self) -> None:
        self.running = True
        return self._main_loop()

    def stop(self):
        self.running = False
        self.update_event.set()
        if self.__server_socket is not None:
            self.__server_socket.close()
        self.join()

    def _main_loop(self):
        self.__server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__server_socket.bind((self.adress, self.port))
        self.__server_socket.listen()
        while self.running:
            try:
                connection, remote_addr_port = self.__server_socket.accept()
            except:
                # might need to be more specific, purpose is to abort
                # server by closing socket
                continue
            # Should probably empty the recv buffer..
            addr = remote_addr_port[0]
            header = self.HEADER + self.LB*2 
            connection.send(header)
            self.pos = 0
            try:
                self._event_loop(connection)
            except:
                pass

    def _event_loop(self, connection: socket.socket):
        while self.running:
            while len(self.events) > self.pos and self.running:
                # TODO might block here and not close server..
                connection.send(self.event_to_message(self.events[self.pos]))
                self.pos += 1
            # There is a risk of context switch here, so add a timeout to be safe
            self.update_event.clear()
            self.update_event.wait(timeout=5)
    
    def event_to_message(self, ev) -> str:
        # TODO ev is not supposed to be strings
        return b"data:" + ev.encode() + b"\n"*2
            

    def add_event(self, event):
        # TODO an actual event class
        self.events.append(event)
        self.update_event.set()