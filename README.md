# Progress (WIP)

Library for taking context based time meassurments and probably graphing it..

The overall concept would be to wrap code, in a context based manner, something like:

```python
@progress.decorator
def my_function():
  with progress.Context("downloads") as ct_download:
    bunch_of_downloads
  print(f"downloads took: {ct_download.elapsed()}")

my_function()

progress.run("A function call I want to time", important_function())
```

And in the end visualize it, probably in some flame graph looking way,
but in essence something tiered:

```
Main 1000 sec
  my_function 201 sec
    downloads 200 sec
  A function call I want to time 400 sec
```

Planning to have a look at plotly to see if I can set something like this up:

```
   |downloads|
   |my_function| |A function call..|
|_Main_____________________________________|
```

Working title, both progress and context already taken on pypi..

## Alternatives

### context

The most similar project to this one is probably [context](https://pypi.org/project/context/) which I would describe as a manual profiler, with a focus on a common visualizer for multiple languages. It is based on logging start and end times in a specific format.

The python library is very light weight, adding a decorator to log start and stop of function calls. If this is all you want, it is probably a good alternative.

This project will probably support the same log format to be compatible with that visualizer.

Currently taking a step back to see if this project actually is different enough to justify it's existence. Context isn't exactly in line with this project, but I need to be explicit with what this project should achieve.

### Others..

There are more libraries than I care to count that adds a context manager, or a descriptor, to either print time elapsed in a more or less advanced manner. But if that is all that is needed, just re-inventing the wheel is better than adding a dependency in my opinion.
