from importlib import import_module

import os
import sys
import argparse
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(TOOLS_DIR))

def handle_input_and_run_tests_for_package(package_name):
    parser = argparse.ArgumentParser(description="Run tests for the {} package.".format(package_name))
    parser.add_argument('--coverage',
                        nargs='?',
                        const=True,
                        default=False,
                        help='compute test coverage (--coverage combine to combine with previous reports)')
    options = parser.parse_args()

    if options.coverage:
        import coverage
        cov = coverage.Coverage(config_file="tools/.coveragerc")
        if options.coverage == 'combine':
            cov.load()
        cov.start()

    # Codecov seems to work only when using loader.discover. It failed to capture line executions
    # for functions like loader.loadTestFromModule or loader.loadTestFromNames.
    test_suites = unittest.defaultTestLoader.discover(package_name)
    suite = unittest.TestSuite(test_suites)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.failures or result.errors:
        sys.exit(1)

    if not result.failures and options.coverage:
        cov.stop()
        cov.data_suffix = False  # Disable suffix so that filename is .coverage
        cov.save()
        cov.html_report()
        print("HTML report saved in directory 'htmlcov'.")
