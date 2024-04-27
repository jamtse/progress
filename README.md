Progress (WIP)

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

There probably is somethng similar out there, possibly log based, but for now I can't find it. For when you don't want a full on profiling, but something more structured, I guess.

Not sure yet if I want to somehow also tie this into progress logs of some kind.