import plotly.graph_objects as go
import unittest
import time

import progress

def bar(context: progress.Context, depth):
    start = context.start_perf / 1000000000
    end = (context.end_perf if context.end_perf is not None else context.get_global_perf_elapsed()) / 1000000000
    perf_elapsed = (end - start)
    proc_end = context.end_process if context.end_process is not None else context.get_global_process_elpased()
    proc_elapsed = (proc_end - context.start_process) / 1000000000
    width = 10
    y = depth * width
    hovertext = "\n".join([
        f"{context.name} ({context.uid})<br />",
        "<br />",
        f"Elapsed time: {perf_elapsed}s<br />",
        f"CPU time: {proc_elapsed}s<br />",
    ])
    return go.Scatter(
        x=[start, start, end, end],
        y=[y, y+width, y+width, y],
        name=context.name,
        fill="toself",
        hoverinfo="text",
        hoveron="fills",
        #hovertemplate=hovertext,
        text=hovertext,
        mode="lines"
        )

def mock_bars(context: progress.Context, depth=0):
    bars = [bar(context, depth)]
    for child in context.children:
        bars.extend(mock_bars(child, depth+1))
    return bars


class TestGraphing(unittest.TestCase):
    def test_graphing(self):
        progress.Context.reset()
        main_context = progress.Context.get_current_context()
        with progress.Context("Init things"):
            time.sleep(0.05)
        with progress.Context("Main loop"):
            time.sleep(0.02)
            with progress.Context("Do important things"):
                time.sleep(0.1)
            with progress.Context("Do important things"):
                time.sleep(0.08)
            with progress.Context("Do important things"):
                time.sleep(0.11)
        time.sleep(0.1)
        bars = mock_bars(main_context)
        
        fig =go.Figure(bars)
        fig.update_layout(hovermode="x unified", dragmode="pan", xaxis_title="Seconds", yaxis_title="Context stack")
        fig.update_yaxes(showticklabels=False)
        fig.show()
    