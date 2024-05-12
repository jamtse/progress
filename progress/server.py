import http.server
import io
import os
import queue
import random
import socket
import threading
import webbrowser

from pathlib import Path
from typing import Dict, Optional, Union

random.seed()


class ProgressServer(threading.Thread):
    """Server for displaying the progress of an application

    Spawn a thread that waits for a connection and then start serving
    server side events with context data.

    Only one connection is served at a time.

    Events are added on to a list that is never dropped, to allow
    re-connecting.
    """
    def __init__(self, port = None, open_browser = 1, web_resources = None) -> None:
        """

        :param port: force use of specific port
        :param open_browser: None/0/1/2 if not None a webbrowser will be
            openened and open_browser valuefed to new parameter.
        """
        self.running = threading.Event()
        self.setup_exception = None
        self.__port = port
        self._adress = "localhost"
        self.__server = None
        self.__handler = ProgressServerHandler
        self.__events = []
        self.__queue = queue.SimpleQueue()
        self.__update_event = threading.Event()
        self.__browser = open_browser
        self._web_resources = web_resources
        super().__init__(name="ProgressServer", daemon=True)
    
    @property
    def port(self):
        return self.__port
    
    @property
    def adress(self):
        return self._adress
    
    def run(self) -> None:
        try:
            self.__setup()
        except Exception as e:
            self.setup_exception = e
            # Wake up other threads waiting for the server to start
            self.running.set()
            self.running.clear()
            raise
        self.__server.serve_forever()

    def __setup(self):
        """Do initial server setup."""
        if self.__port is not None:
            self.__server = ThreadingProgressServer(
                (self._adress, self.__port),
                self.__handler,
                self._event_loop,
                bind_and_activate=True,
                web_resources=self._web_resources,
                )
        else:
            # Attempt several random ports in the private port range
            exception = None
            for _ in range(50):
                self.__port = random.randrange(49152, 65535)
                try:
                    self.__server = ThreadingProgressServer(
                        (self._adress, self.__port),
                        self.__handler,
                        self._event_loop,
                        bind_and_activate=True,
                        web_resources=self._web_resources,
                        )
                    break
                except OSError as e:
                    exception = e
            else:
                raise exception
        self.__server.block_on_close = False
        self.__server.daemon_threads = True
        # Open a browser window, unless disabled
        if self.__browser is not None:
            webbrowser.open(f"http://{self._adress}:{self.port}/", new = self.__browser)
        # Start event management thread
        self.running.set()
        threading.Thread(target=self.__event_manager, daemon=True).start()
    
    def __event_manager(self):
        """Constrains event writes to one thread.
        
        Thread safety reasoning might half assed, especially with free
        threads in cython on the horison, but it roughly relies on the
        assumption that since there is just one writer, and the list
        only grows, lock free access is OK.  Even if the list ends up
        re-alocated in the underlaying structure, at worst the reader
        won't have the latest content for a bit.

        Note that if there is a re-init, the list must not shrink, as
        that would mess with the servers read positions, it might be
        OK to replace the previous Events with None to indicate that
        they are now invalid however, to allow the instances to be
        freed.
        """
        while True:
            event = self.__queue.get()
            if not self.running.is_set(): break
            self.__events.append(event)
            self.__update_event.set()
            

    def wait_until_ready(self, timeout=None) -> bool:
        """Wait until server is up and running.
        
        Main purpose is to allow detection of issues setting up the
        socket.

        :return: True if server is up and running
        :raises OSError: if failed to bind the port
        """
        running = self.running.wait(timeout=timeout)
        if self.setup_exception is not None:
            raise self.setup_exception
        return running

    def stop(self):
        """Shut down server.
        
        Will block until thread is properly shut down.

        Note that thread is marked as daemon, so should not block
        sudden shutdowns.
        """
        self.running.clear()
        # Noop event for waking up the thread manager
        self.add_event(None)
        # Wake up servers waiting for events
        self.__update_event.set()
        if self.__server is not None:
            self.__server.server_close()
            self.__server.shutdown()
        self.join()

    def _event_loop(self, connection):
        if isinstance(connection, socket.socket):
            def send(data): connection.send(data)
        elif isinstance(connection, io.BufferedIOBase):
            def send(data): connection.write(data)
        pos = 0
        while self.running.is_set():
            while len(self.__events) > pos and self.running.is_set():
                event = self.__events[pos]
                if event is not None:
                    # TODO might block here and not close server..
                    send(self._event_to_message(event))
                pos += 1
            # There is a risk of context switch here, so add a timeout to be safe
            self.__update_event.clear()
            self.__update_event.wait(timeout=5)
        # running aborted, but connection still up, send abort
        send(self.__shutdown_message())
    
    @staticmethod
    def __shutdown_message() -> str:
        return b"event: abort\ndata: {\"reason\": \"shutdown\"}\n\n"
    
    def _event_to_message(self, ev) -> str:
        # TODO ev is not supposed to be strings
        return b"data: " + ev.encode() + b"\n"*2

    def add_event(self, event):
        # Hand over to queue to avoid blocking
        self.__queue.put(event)

class ThreadingProgressServer(http.server.ThreadingHTTPServer):
    def __init__(
            self,
            server_address,
            RequestHandlerClass,
            event_loop_callback,
            *,
            web_resources: Optional[Dict[str, Union[Path, bytes]]] = None,
            bind_and_activate: bool = True,
            ) -> None:
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)
        self._event_loop_callback = event_loop_callback
        self._web_resources = {
                # TODO replace, path to the root dir isn't functional in library
                "/": Path(os.path.realpath("serversidetest.html"))
            }
        if web_resources is not None:
            self._web_resources.update(web_resources)


class ProgressServerHandler(http.server.BaseHTTPRequestHandler):
    server: ThreadingProgressServer
    """Handler for serving the Status page and event stream."""
    def log_message(self, format, *args) -> None:
        pass

    def do_HEAD(self):
        self.__handle_request(just_headers=True)

    def do_GET(self):
        self.__handle_request(just_headers=False)

    def __handle_request(self, just_headers: bool):
        if self.path == "/events":
            self.__serve_event_stream(just_headers)
        elif self.path in self.server._web_resources:
            self.__serve_content(just_headers)
        else:
            self.send_error(404, "Not Found")
            self.end_headers()
        
    def __serve_event_stream(self, just_headers: bool):
        self.send_response(200, "OK")
        self.send_header("Server", "ProgressServer")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        # For serving a local file
        #self.send_header("access-control-allow-origin", "null")
        self.end_headers()
        if just_headers:
            return
        try:
            self.server._event_loop_callback(self.wfile)
        except Exception as e:
            # Just bail out silently, most likely the user closed page
            pass
    
    def __serve_content(self, just_headers: bool):
        resource = self.server._web_resources[self.path]
        if isinstance(resource, Path):
            if resource.is_file():
                with open(resource, "rb") as fp:
                    content = fp.read()
            else:
                self.send_error("500", "Internal server error")
                self.end_headers()
                raise Exception(f"Resource path for {self.path} is not a file: {resource}")
        elif isinstance(resource, bytes):
            content = resource
        else:
            raise Exception(f"Resource data for path {self.path} is not valid type: {type(resource)}")
        self.send_response(200, "OK")
        self.end_headers()
        if just_headers:
            return
        self.wfile.write(content)
