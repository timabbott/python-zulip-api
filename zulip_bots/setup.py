#!/usr/bin/env python3

import os
import sys
from typing import Any, Dict, Optional

ZULIP_BOTS_VERSION = "0.7.1"
IS_PYPA_PACKAGE = False


package_data = {
    '': ['doc.md', '*.conf', 'assets/*'],
    'zulip_bots': ['py.typed'],
}

# IS_PYPA_PACKAGE is set to True by tools/release-packages
# before making a PyPA release.
if not IS_PYPA_PACKAGE:
    package_data[''].append('fixtures/*.json')
    package_data[''].append('logo.*')

with open("README.md") as fh:
    long_description = fh.read()

# We should be installable with either setuptools or distutils.
package_info = dict(
    name='zulip_bots',
    version=ZULIP_BOTS_VERSION,
    description='Zulip\'s Bot framework',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Zulip Open Source Project',
    author_email='zulip-devel@googlegroups.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Communications :: Chat',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    python_requires='>=3.6',
    url='https://www.zulip.org/',
    project_urls={
        "Source": "https://github.com/zulip/python-zulip-api/",
        "Documentation": "https://zulip.com/api",
    },
    entry_points={
        'console_scripts': [
            'zulip-run-bot=zulip_bots.run:main',
            'zulip-terminal=zulip_bots.terminal:main'
        ],
    },
    include_package_data=True,
)  # type: Dict[str, Any]

setuptools_info = dict(
    install_requires=[
        'pip',
        'zulip',
        'html2text',
        'lxml',
        'BeautifulSoup4',
        'entrypoints',
    ],
)

try:
    from setuptools import setup, find_packages
    package_info.update(setuptools_info)
    package_info['packages'] = find_packages()
    package_info['package_data'] = package_data

except ImportError:
    from distutils.core import setup
    from distutils.version import LooseVersion
    from importlib import import_module

    # Manual dependency check
    def check_dependency_manually(module_name: str, version: Optional[str] = None) -> None:
        try:
            module = import_module(module_name)  # type: Any
            if version is not None:
                assert(LooseVersion(module.__version__) >= LooseVersion(version))
        except (ImportError, AssertionError):
            if version is not None:
                print("{name}>={version} is not installed.".format(
                    name=module_name, version=version), file=sys.stderr)
            else:
                print("{name} is not installed.".format(name=module_name), file=sys.stderr)
            sys.exit(1)

    check_dependency_manually('zulip')
    check_dependency_manually('mock', '2.0.0')
    check_dependency_manually('html2text')
    check_dependency_manually('PyDictionary')

    # Include all submodules under bots/
    package_list = ['zulip_bots']
    dirs = os.listdir('zulip_bots/bots/')
    for dir_name in dirs:
        if os.path.isdir(os.path.join('zulip_bots/bots/', dir_name)):
            package_list.append('zulip_bots.bots.' + dir_name)
    package_info['packages'] = package_list

setup(**package_info)
