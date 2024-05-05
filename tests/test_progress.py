import unittest
import time

import progress


class TestProgress(unittest.TestCase):
    def test_elapsed(self):
        progress.Context.reset()
        with progress.Context("test") as pr:
            time.sleep(1)
            self.assertAlmostEqual(1, pr.perf_elapsed()/1000000000, 2)
            self.assertAlmostEqual(0, pr.process_elapsed()/1000000000, 2)
    
    def test_with_layers(self):
        progress.Context.reset()
        main_context = progress.Context.get_current_context()
        with progress.Context("a") as c1:
            self.assertEqual(c1, progress.Context.get_current_context())
            with progress.Context("b") as c2:
                self.assertEqual(c2, progress.Context.get_current_context())
            self.assertTrue(c2.closed())
            self.assertEqual(c1, progress.Context.get_current_context())
        self.assertTrue(c1.closed())
        self.assertEqual(main_context, progress.Context.get_current_context())
        self.assertFalse(main_context.closed())
    
    def test_decorator(self):
        @progress.Context.decorate()
        def decorated(input):
            self.assertEqual("decorated", progress.Context.get_current_context().name)
            return input
        
        @progress.Context.decorate(name="My context")
        def decorated2(input):
            self.assertEqual("My context", progress.Context.get_current_context().name)
            return input
        
        data = "APA"
        ret = decorated(data)
        self.assertEqual(data, ret)


        data = "Svans"
        ret = decorated2(data)
        self.assertEqual(data, ret)
    
    def test_double_decorator_preserve_name(self):
        def misc_decorator(f):
            def wrapper(*arg, **args):
                assert(f.__name__ == "decorated")
                return f(*arg, **args)
            return wrapper
        
        @misc_decorator
        @progress.Context.decorate()
        def decorated(input):
            self.assertEqual("decorated", progress.Context.get_current_context().name)
            return input
        
        data = "APA"
        ret = decorated(data)
        self.assertEqual(data, ret)

    def test_function_wrapper(self):
        def function_for_test(input: str) -> str:
            self.assertEqual("function_for_test", progress.Context.get_current_context().name)
            return input
        
        data = "information"
        ret = progress.Context.wrap(function_for_test)(data)
        self.assertEqual(data, ret)

    def test_decorator_as_wrapper(self):
        def function_for_test(input: str) -> str:
            self.assertEqual("another_name", progress.Context.get_current_context().name)
            return input
        
        data = "information"
        ret = progress.Context.decorate(name="another_name")(function_for_test)(data)
        self.assertEqual(data, ret)