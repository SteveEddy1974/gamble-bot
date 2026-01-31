import unittest
import runpy
import sys


class TestMainCLIInvocation(unittest.TestCase):
    def test_module_invocation_parses_args_and_exits(self):
        old_argv = sys.argv[:]
        try:
            sys.argv = ['main.py', '--iterations', '0']
            # Running module as __main__ should execute argparse lines and call main with iterations=0
            runpy.run_module('main', run_name='__main__')
        finally:
            sys.argv = old_argv


if __name__ == '__main__':
    unittest.main()
