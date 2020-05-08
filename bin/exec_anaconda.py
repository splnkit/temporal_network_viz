# Copyright (C) 2015-2019 Splunk Inc. All Rights Reserved.

# To be used in accordance with the README file in Python for Scientific
# Computing (PSC). That is, exec_anaconda.py is available to be copied and
# placed into your applications as needed to allow for the execution of Splunk
# Custom Search Commands and cross-platform module imports. See the PSC README
# file for more details.
import json
import os
import platform
import stat
import subprocess
import sys
import time
import traceback

from splunk_path_util import get_apps_path


# NOTE: This file must be Python 2 and 3 compatible until
# Splunk Enterprise drops support for Python2.

# Prefix of the directory name where PSC is installed
PSC_PATH_PREFIX = 'Splunk_SA_Scientific_Python_'

SUPPORTED_SYSTEMS = {
    ('Linux', 'x86_64'): 'linux_x86_64',
    ('Darwin', 'x86_64'): 'darwin_x86_64',
    ('Windows', 'AMD64'): 'windows_x86_64',
}


def check_python_version():
    if sys.version_info[0] < 3:
        raise Exception(
            'This version of MLTK must be run under Python3. Please consult MLTK documentation for more information'
        )


def exec_anaconda():
    """Re-execute the current Python script using the Anaconda Python
    interpreter included with Splunk_SA_Scientific_Python.

    After executing this function, you can safely import the Python
    libraries included in Splunk_SA_Scientific_Python (e.g. numpy).

    Canonical usage is to put the following at the *top* of your
    Python script (before any other imports):

       import exec_anaconda
       exec_anaconda.exec_anaconda()

       # Your other imports should now work.
       import numpy as np
       import pandas as pd
       ...
    """
    system = (platform.system(), platform.machine())
    if system not in SUPPORTED_SYSTEMS:
        raise Exception('Unsupported platform: %s %s' % (system))

    sa_scipy = '%s%s' % (PSC_PATH_PREFIX, SUPPORTED_SYSTEMS[system])

    sa_path = os.path.join(get_apps_path(), sa_scipy)
    if not os.path.isdir(sa_path):
        raise Exception('Failed to find Python for Scientific Computing Add-on (%s)' % sa_scipy)

    system_path = os.path.join(sa_path, 'bin', '%s' % (SUPPORTED_SYSTEMS[system]),'lib', 'python3.7')
    system_packages = os.path.join(sa_path, 'bin', '%s' % (SUPPORTED_SYSTEMS[system]),'lib', 'python3.7', 'site-packages')

    sys.path.append(system_path)
    sys.path.append(system_packages)




def fix_sys_path():
    # After shelling into PSC's Python interpreter, we no longer have access
    # to Splunk core's Python path to import stuff from there. So we retrieve
    # that path from the environment variable we set before.
    splunk_python_path = os.environ.get('SPLUNK_CORE_PYTHONPATH')
    if not splunk_python_path:
        raise Exception('Can not find Splunk core Python path')
    try:
        splunk_python_path = json.loads(splunk_python_path)
    except Exception as e:
        raise Exception('Can not parse Splunk core Python path: %r' % e)
    for item in splunk_python_path:
        if item not in sys.path:
            sys.path.append(item)





def exec_anaconda_or_die():
    try:
        exec_anaconda()
    except Exception as e:
        print('Failed to activate Conda environment: %r' % e, sys.stderr)
        with open("/Users/gburgett/Downloads/tnerror.log", "w") as ofile:
            ofile.write("%s\n%s\n" % (e,sys.stderr))
        sys.exit(1)
