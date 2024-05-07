import threading
import time

from functools import wraps
from typing import Dict, List, Optional


class Context:
    # class variables
    __global_perf_start = time.perf_counter_ns()
    # TODO switch to thread_time_ns and probably get rid of the global
    __global_process_start = time.process_time_ns()
    __global_context: Dict[str, List["Context"]] = {}
    __global_id_counter = 0
    __global_id_counter_mutex = threading.Lock()
    # instance variables
    name: str
    uid: int
    start_perf: int
    start_process: int
    end_perf: Optional[int]
    end_process: Optional[int]
    children: List["Context"]

    def __init__(self, name):
        self.name = name
        self.uid = self.__get_uid()
        self.start_perf = self.get_global_perf_elapsed()
        self.start_process = self.get_global_process_elpased()
        self.end_perf = None
        self.end_process = None
        self.children = []
    
    @classmethod
    def __get_uid(cls) -> int:
        with cls.__global_id_counter_mutex:
            uid = cls.__global_id_counter
            cls.__global_id_counter += 1
        return uid
    
    @classmethod
    def reset(cls):
        cls.__global_perf_start = time.perf_counter_ns()
        cls.__global_process_start = time.process_time_ns()
        with cls.__global_id_counter_mutex:
            cls.__global_id_counter = 0
        cls.__global_context = {
            threading.current_thread().name: [Context("Main")]
        }
    
    @classmethod
    def get_global_perf_elapsed(cls) -> int:
        return time.perf_counter_ns() - cls.__global_perf_start

    @classmethod
    def get_global_process_elpased(cls) -> int:
        return time.process_time_ns() - cls.__global_process_start
    
    @classmethod
    def get_current_context(cls) -> Optional["Context"]:
        thread_name = threading.current_thread().name
        context: Optional[Context] = cls.__global_context.get(thread_name)
        if context is not None:
            context = context[-1].__current_context()
        return context
    
    @classmethod
    def __set_context(cls, context: "Context"):
        parent = cls.get_current_context()
        if parent is None:
            thread_name = threading.current_thread().name
            context_list = cls.__global_context.setdefault(thread_name, [])
            context_list.append(context)
        else:
            parent.__add_context(context)
    
    def __current_context(self) -> "Context":
        if len(self.children) > 0 and not self.children[-1].closed():
            return self.children[-1].__current_context()
        return self
    
    def __add_context(self, context: "Context"):
        self.children.append(context)
    
    def __enter__(self):
        self.__set_context(self)
        return self

    def __exit__(self ,_type, _value, _traceback):
        self.end_perf = self.get_global_perf_elapsed()
        self.end_process = self.get_global_process_elpased()
    
    @classmethod
    def decorate(cls, name=None):
        def decorator(func):
            nonlocal name
            if name is None:
                name = func.__name__
            @wraps(func)
            def wrapper(*arg, **args):
                with Context(name):
                    ret = func(*arg, **args)
                return ret
            
            return wrapper
        return decorator

    @classmethod
    def wrap(cls, func):
        name = func.__name__
        @wraps(func)
        def wrapper(*arg, **args):
            with Context(name):
                ret = func(*arg, **args)
            return ret
        
        return wrapper
    
    def closed(self) -> bool:
        return self.end_perf is not None

    def perf_elapsed(self) -> int:
        if self.closed():
            return self.end_perf -self.start_perf
        else:
            return self.get_global_perf_elapsed() - self.start_perf
    
    def process_elapsed(self) -> int:
        if self.closed():
            return self.end_process - self.start_process
        else:
            return self.get_global_process_elpased() - self.start_process
    
    @classmethod
    def print_perf_progress(cls):
        context_list = cls.__global_context.get(threading.current_thread().name)
        def print_context_indent(context: Context, indent = 0):
            print(f"{' '*indent}{context.name} {context.perf_elapsed()} {'⌛' if not context.closed() else ''}")
            for child in context.children:
                print_context_indent(child, indent + 2)

        for context in context_list:
            print_context_indent(context)
    
# Initiate the "Main" Context at import
Context.reset()