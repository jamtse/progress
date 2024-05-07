# Progress (WIP)

Library for taking context based time meassurments and probably graphing it..

The overall concept would be to wrap code, in a context based manner, something like:

```python
from progress import Context as Ctx

@Ctx.decorate("Most of the work")
def my_function():
  with Ctx("downloads") as ct_download:
    # bunch_of_downloads..
    Ctx.marker("Point in time to take note of")
    # more downloads..
  print(f"downloads took: {ct_download.elapsed()}")

  Ctx.decorate("A function call I want to time", important_function)()

my_function()

Ctx.wrap(function_that_speaks_for_itself)("function parameter")
```

And in the end visualize it, probably in some flame graph looking way,
but in essence something tiered:

```
Main 1000 sec
  Most of the work 601 sec
    downloads 200 sec
      @190(90) Point in time to take note of
    A function call I want to time 400 sec
  function_that_speaks_for_itself 200
```

Planning to have a look at plotly to see if I can set something like this up:

```
   |downloads| |A function call..|
   |Most of the work              | |function_that_speaks_for_itself|
|_Main___________________________________________________________________|
```

Working title, both progress and context already taken on pypi..

## Design todo

- Do I actually want to keep the context in memory? storing start and stop with metadata to file should be sufficient for most use cases. Even if I want to visualize it live, I could just monitor the file.
- Do I really want the "Main" context that starts at import? the developers can create that themselves if they want it after all.
- Clarify the goals for the live monitoring. As always hard to indicate how far along you are without knowledge of the future, but perhaps it can be initialized with a few named context that are expected to come in series, and how large they are expected to be in %, to give an estimation. Also should the monitoring be a separate thing or something that can be started from inside the the monitored application.
- Visualization in plotly or as a svg, with the assumption that the live view is needed, need to test out the existing context viewer (see below in alternatives) and determine if it's needed at all.
- How to handle threads. Simplest would be to just to consider them separate, but perhaps allowing the developer to decide if it should be flattened into the same graph (perhaps they wait for the threads to be done). I also think there would be value in flattening the thread graphs when they are sperate, so that if we see that two threads don't overlap, they can be combined to not get excessive amount of graphs.
- I don't think the existing context support both real time and cpu time (but need to verify), so might need a new log format even if that is used instead of in memory.
- Do I want contextual logs/sample points? Not aiming for a complete log framework, but might be useful if they can be marked out in the graph for when you just want a marker, without creating or ending a context.


## Alternatives

### context

The most similar project to this one is probably [context](https://pypi.org/project/context/) which I would describe as a manual profiler, with a focus on a common visualizer for multiple languages. It is based on logging start and end times in a specific format.

The python library is very light weight, adding a decorator to log start and stop of function calls. If this is all you want, it is probably a good alternative.

This project will probably support the same log format to be compatible with that visualizer.

Currently taking a step back to see if this project actually is different enough to justify it's existence. Context isn't exactly in line with this project, but I need to be explicit with what this project should achieve.

### Others..

There are more libraries than I care to count that adds a context manager, or a descriptor, to either print time elapsed in a more or less advanced manner. But if that is all that is needed, just re-inventing the wheel is better than adding a dependency in my opinion.

## Design (WIP)

Python_app -> Context_log_file (dump_at_end/live) (Compatible with context viewer ideally)
Python_app -> Human readable text tree visualization (dump at end/live?)

Python_app -> Server_thread (live)
Server_thread -> server_side_events # only accept one client
Browser <- Server_side_events

### Python_app

The monitored application introduces the decorators etc. which appends data to a log file.

It can also optionally spawn a background `Server_app` with `Popen` and call `webbrowser.open()` on a local html file. to present the data live without affecting the performance of the application needlessly (That said, it probably wouldn't be much of a performance hit to send the data as it becomes available over a socket instead of writing to file).

### Server_thread

A simple socket server which listens for one connection at a time and then serves a http response for server side events. It proceeds to serve all events that has happened so far and then waiting for more data to be appended by keeping the file open for reading, ignoring the EOF exception.

For this simple use case there should be no reason to bother with what the client asks for, just throw away all client data and serve something like:

```
HTTP/1.1 200 OK
Server: Identifier for the server/make something up or skip it
X-Accel-Buffering: no
Content-Type: text/event-stream
Cache-Control: no-cache

Start of event data separated by double newlines
```

May likely need `access-control-allow-origin` as well to specify that localhost may use the data source in scripts. null can be used if we are serving a local file. potentially we could also serve the web page this way.. but there is some risk of actually having to read what the client wants then (otherwise we could confuse a request for favicon with the request for the stream)

Note that newlines should be CRLF according to spec
Also note that below HTTP/2 the maximum amount of connections between the browser and a server is 6. In HTTP/2 this would be negotiated (or defaulted to 100). It's probably not an issue for this use case, so just go with 1.1 initially.

Input file and port taken as arguments

### Browser

A static web page which uses serverside events to get the state of the execution and present that as a graph which updates regularely (more often then the events, as time passes, non terminated contexts will need to grow)

Can be implemented with javascript or wasm

```JS
const evtSource = new EventSource("//localhost:<port>")

evtSource.onmessage = (event) => { do something with event.data };
```

Could also make use of the event field could also use `.addEventListener("name_of_event", (event) => {});` Might be useful.

### Syncing

Need to communicate the port to the static web page somehow, or decide on a static one.

### Overhead considerations

There will always be overhead of some kind, either from writing to file or storing in memory. I'm making the assumption that this won't be used on pieces of code that are called millions of times, so I'm betting on storing it in memory for the time beeing (the live scenarios don't technically need this, I could poll a file from a separate application).