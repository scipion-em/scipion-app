#!/usr/bin/env python
# **************************************************************************
# *
# * Authors:    J. M. De la Rosa Trevin (delarosatrevin@scilifelab.se) [1]
# *             I. Foche Perez (ifoche@cnb.csic.es) [2]
# *             P. Conesa (pconesa@cnb.csic.es) [2]
# *
# *  [1] SciLifeLab, Stockholm University
# *  [2] Unidad de Bioinformatica of Centro Nacional de Biotecnologia, CSIC
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 2 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************
"""
Main entry point to scipion. It launches the gui, tests, etc.
"""
from importlib import util
import site
import sys
import os
from os.path import join, exists, dirname, expanduser


import subprocess
import pyworkflow
from configparser import ConfigParser, ParsingError  # Python 3
from scipion.constants import *
from scipion.utils import (getScipionHome, getInstallPath,
                           getTemplatesPath, getScriptsPath)

__version__ = 'v3.0'
__nickname__ = DEVEL
__releasedate__ = ''

SCIPION_DOMAIN = "pwem"


SCIPION_HOME = getScipionHome()

# Some pw_*.py scripts under 'apps' folder change the current working
# directory to the SCIPION_HOME, so let's keep the current working
# directory in case we need it
SCIPION_CWD = os.path.abspath(os.getcwd())

# Scipion path to its own scripts
SCIPION_SCRIPTS = getScriptsPath()
# Scipion path to install
SCIPION_INSTALL = getInstallPath()
#
# If we don't have a local user installation, create it.
#

# Default values for configuration files.
SCIPION_CONFIG = join(SCIPION_HOME, 'config', 'scipion.conf')
SCIPION_LOCAL_CONFIG = expanduser(os.environ.get('SCIPION_LOCAL_CONFIG',
                                                 '~/.config/scipion/scipion.conf'))

# Allow the user to override them (and remove them from sys.argv).
while len(sys.argv) > 2 and sys.argv[1].startswith('--'):
    arg = sys.argv.pop(1)
    value = sys.argv.pop(1)
    if arg == '--config':
        # If we pass the arguments "--config some_path/scipion.conf",
        # only the config files in that path will be read.
        SCIPION_CONFIG = os.path.abspath(os.path.expanduser(value))
        SCIPION_LOCAL_CONFIG = SCIPION_CONFIG  # global and local are the same!
    else:
        sys.exit('Unknown argument: %s' % arg)

SCIPION_PROTOCOLS = join(dirname(SCIPION_CONFIG), 'protocols.conf')

# Allow the name of the host configuration to be changed.
# This is useful for having the same central installation that
# could be used from different environments (cluster vs workstations)
SCIPION_HOSTS = join(dirname(SCIPION_CONFIG), 'hosts.conf')


# Check for old configuration files and tell the user to update.
if SCIPION_LOCAL_CONFIG != SCIPION_CONFIG and exists(SCIPION_LOCAL_CONFIG):
    cf = ConfigParser()
    cf.optionxform = str  # keep case (stackoverflow.com/questions/1611799)
    try:
        cf.read(SCIPION_LOCAL_CONFIG)
    except ParsingError:
        sys.exit("%s\nPlease fix the configuration file." % sys.exc_info()[1])

#
# Check the version if in devel mode (i.e no release date yet)
#

if not __releasedate__:
    # Find out if the is a .git directory
    if exists(join(SCIPION_HOME, '.git')):
        def call(cmd):
            return subprocess.Popen(cmd, shell=True, cwd=SCIPION_HOME).wait()
        if call('which git > /dev/null') == 0:  # Means git command is found

            gitBranch = str(subprocess.check_output("git branch | grep \\* ", cwd=SCIPION_HOME, shell=True))
            gitBranch = gitBranch.split("*")[1].strip()
            commitLine = str(subprocess.check_output(['git', 'log', '-1',
                                                      '--pretty=format:%h %ci'],
                                                     cwd=SCIPION_HOME))
            gitCommit, __releasedate__ = commitLine.split()[:2]
            if gitCommit.startswith("b'"):
                gitCommit = gitCommit[2:]
            __nickname__ += ' (%s %s)' % (gitBranch, gitCommit)

    # If in a future we release  a nightly build, we could add the .devel_version


def getVersion(long=True):
    if long:
        return "%s (%s) %s" % (__version__, __releasedate__, __nickname__)
    else:
        return __version__


def printVersion():
    """ Print Scipion version """
    # Print the version and some more info
    sys.stdout.write('\nScipion %s\n\n' % getVersion())

#
# Initialize variables from config file.
#

for confFile in [SCIPION_CONFIG, SCIPION_LOCAL_CONFIG,
                 SCIPION_PROTOCOLS, SCIPION_HOSTS]:
    if not exists(confFile) and (len(sys.argv) == 1 or sys.argv[1] != MODE_CONFIG):
        sys.exit('Missing file:  %s\nPlease run scipion in config mode to fix '
                 'your configuration:\n  "scipion config"  to fix your '
                 'configuration' % confFile)


def getPyworkflowPath():
    return dirname(pyworkflow.__file__)


def getPythonPackagesFolder():

    return site.getsitepackages()[0]


def getModuleFolder(moduleName):
    """ Returns the path of a module without importing it"""

    spec = util.find_spec(moduleName)
    return dirname(spec.origin)


def getPwemFolder():

    return getModuleFolder(SCIPION_DOMAIN)


def getXmippGhostFolder():

    return join(getPwemFolder(), "xmipp-ghost")

# VARS will contain all the relevant environment variables, including
# directories and packages.
VARS = {
    'PW_APPS': join(getPyworkflowPath(), 'apps'),
    'SCIPION_INSTALL': SCIPION_INSTALL,
    'SCIPION_HOME': SCIPION_HOME,
    'SCIPION_CWD': SCIPION_CWD,
    'SCIPION_VERSION': getVersion(),
    'SCIPION_PYTHON': 'python',
    'SCIPION_CONFIG': SCIPION_CONFIG,
    'SCIPION_LOCAL_CONFIG': SCIPION_LOCAL_CONFIG,
    'SCIPION_PROTOCOLS': SCIPION_PROTOCOLS,
    'SCIPION_HOSTS': SCIPION_HOSTS,
    'SCIPION_SCRIPTS': SCIPION_SCRIPTS,
    'SCIPION_TEMPLATES': getTemplatesPath(),
    'SCIPION_DOMAIN': SCIPION_DOMAIN,
    pyworkflow.PW_ALT_TESTS_CMD:
        os.environ.get(pyworkflow.PW_ALT_TESTS_CMD,
                       '%s %s' % (SCIPION_EP, MODE_TESTS))
}

try:
    config = ConfigParser()
    config.optionxform = str  # keep case (stackoverflow.com/questions/1611799)
    config.read([SCIPION_CONFIG, SCIPION_LOCAL_CONFIG])

    def getPaths(section):
        return dict([(key, join(SCIPION_HOME,
                                os.path.expanduser(os.path.expandvars(path))))
                     for key, path in config.items(section)])  # works in 2.4

    def getValues(section):
        return dict([(key, value)
                     for key, value in config.items(section)])  # works in 2.4

    DIRS_GLOBAL = getPaths('DIRS_GLOBAL')
    DIRS_LOCAL = getPaths('DIRS_LOCAL')
    PACKAGES = getPaths('PACKAGES')
    if config.has_section('VARIABLES'):
        VARIABLES = getValues('VARIABLES')
    else:  # For now, allow old scipion.conf without the VARIABLES section
        sys.stdout.write("Warning: Missing section 'VARIABLES' in the "
                         "configuration file ~/.config/scipion/scipion.conf\n")
        VARIABLES = {}

    REMOTE = dict(config.items('REMOTE'))
    BUILD = dict(config.items('BUILD'))

    for d in DIRS_LOCAL.values():
        if not exists(d):
            sys.stdout.write('Creating directory %s ...\n' % d)
            os.makedirs(d)

    SCIPION_SOFTWARE = DIRS_GLOBAL['SCIPION_SOFTWARE']
    XMIPP_LIB = join(PACKAGES['XMIPP_HOME'], 'lib')
    XMIPP_BINDINGS = join(PACKAGES['XMIPP_HOME'], 'bindings', 'python')

    PATH = os.pathsep.join(
        [dirname(sys.executable),
         BUILD['JAVA_BINDIR'],
         BUILD['MPI_BINDIR'],
         BUILD['CUDA_BIN'],
         os.environ.get('PATH', '')]
    )
    LD_LIBRARY_PATH = os.pathsep.join(
        [join(SCIPION_SOFTWARE, 'lib'),
         BUILD['MPI_LIBDIR'],
         BUILD['CUDA_LIB'],
         XMIPP_LIB,
         os.environ.get('LD_LIBRARY_PATH', '')]
    )
    ignorePythonpath = os.environ.get('SCIPION_IGNORE_PYTHONPATH', False)
    PYTHONPATH_LIST = [SCIPION_HOME,
                       XMIPP_BINDINGS,
                       os.environ.get('PYTHONPATH', '') if not ignorePythonpath else "",
                       getXmippGhostFolder()]  # To be able to open scipion without xmipp

    if 'SCIPION_NOGUI' in os.environ:
        PYTHONPATH_LIST.insert(0, join(getPyworkflowPath(), 'gui', 'no-tkinter'))

    PYTHONPATH = os.pathsep.join(PYTHONPATH_LIST)

    VARS.update({
        'PATH': PATH,
        'PYTHONPATH': PYTHONPATH,
        'LD_LIBRARY_PATH': LD_LIBRARY_PATH})

    VARS.update(DIRS_GLOBAL)
    VARS.update(DIRS_LOCAL)
    VARS.update(PACKAGES)
    VARS.update(REMOTE)
    VARS.update(BUILD)
    VARS.update(VARIABLES)
except Exception as e:
    if len(sys.argv) == 1 or sys.argv[1] != MODE_CONFIG:
        # This way of catching exceptions works with Python 2 & 3
        sys.stderr.write('Error at main: %s\n' % e)
        sys.stdout.write('Please check the configuration file %s and '
                         'try again.\n' % SCIPION_CONFIG)
        sys.exit(1)


#
# Auxiliary functions to run commands in our environment, one of our
# scripts, or one of our "apps"
#

def envOn(varName):
    value = os.environ.get(varName, '').lower()
    return value in ['1', 'true', 'on', 'yes']


def runCmd(cmd, args=''):
    """ Runs ANY command with its arguments"""
    if isinstance(args, list):
        args = ' '.join('"%s"' % x for x in args)

    cmd = '%s %s' % (cmd, args)

    os.environ.update(VARS)
    sys.stdout.write(">>>>> %s\n" % cmd)
    result = os.system(cmd)
    if not -256 < result < 256:
        result = 1  # because if not, 256 is confused with 0 !
    sys.exit(result)


# The following functions require a working SCIPION_PYTHON
def runScript(scriptCmd, args='', chdir=True):
    """"Runs a PYTHON script appending the profiling prefix if ON"""
    if chdir:
        os.chdir(SCIPION_HOME)

    if envOn('SCIPION_PROFILE'):
        profileStr = '-m cProfile -o output.profile'
    else:
        profileStr = ''
    cmd = '%s %s %s' % (VARS['SCIPION_PYTHON'], profileStr, scriptCmd)
    runCmd(cmd, args)


def runApp(app, args='', chdir=True):
    """Runs an app provided by pyworkflow"""
    runScript(join(VARS['PW_APPS'], app), args=args, chdir=chdir)


def main():
    printVersion()
    # See in which "mode" the script is called. By default, it's MODE_MANAGER.
    n = len(sys.argv)
    # Default to MANAGER_MODE
    mode = sys.argv[1] if n > 1 else MODE_MANAGER

    # Check mode
    if mode == MODE_MANAGER:
        runApp('pw_manager.py')

    elif mode == MODE_LAST:
        runApp('pw_project.py', args='last')

    elif mode == MODE_HERE:
        runApp('pw_project.py', args='here')
        
    elif mode == MODE_PROJECT:
        runApp('pw_project.py', args=sys.argv[2:])

    elif mode == MODE_TESTS or mode == MODE_TEST:
        runApp('pw_run_tests.py', args=sys.argv[2:])

    elif mode == MODE_TEST_DATA:
        runApp('pw_sync_data.py', args=sys.argv[2:])

    elif mode in MODE_VIEWER:
        runApp('pw_viewer.py', args=sys.argv[2:], chdir=False)

    # elif mode == MODE_INSTALL_BINS:
    #     runScript('scipion install %s' % ' '.join(sys.argv[2:]))

    elif mode in PLUGIN_MODES:
        cwd = os.getcwd()
        os.chdir(SCIPION_HOME)

        os.environ.update(VARS)
        args = ' '.join(sys.argv)

        runScript('%s %s' % (join(VARS['SCIPION_INSTALL'], 'install-plugin.py'), args))

    elif mode == MODE_PLUGINS:
        runScript(join(VARS['SCIPION_INSTALL'], 'plugin_manager.py'))

    elif mode == MODE_CONFIG:
        runApp(join(SCIPION_SCRIPTS, 'config.py'), sys.argv[2:])

    elif mode == MODE_VERSION:
        # Just exit, Scipion version will be printed anyway
        sys.exit(0)

    elif mode == MODE_RUNPROTOCOL:
        assert (n == 6 or n == 7), 'runprotocol takes exactly 5 arguments, not %d' % (n - 1)
        # this could be pw_protocol_run.py or pw_protocol_mpirun.py
        protocolApp = sys.argv[2]
        # This should be (projectPath, protocolDb and protocolId)
        runApp(protocolApp, args=sys.argv[3:])
        
    elif mode == MODE_PROTOCOLS:
        runApp('pw_protocol_list.py', args=sys.argv[2:])

    elif mode == MODE_ENV:
        # Print all the environment variables needed to run scipion.
        for key in sorted(VARS):
            sys.stdout.write('export %s="%s"\n' % (key, VARS[key]))

        sys.exit(0)

    elif mode == MODE_RUN:
        # Run any command with the environment of scipion loaded.
        runCmd(' '.join(['"%s"' % arg for arg in sys.argv[2:]]))
        
    elif mode == MODE_PYTHON:
        runScript(' '.join(['"%s"' % arg for arg in sys.argv[2:]]), 
                  chdir=False)

    elif mode == MODE_TUTORIAL:
        runApp(join(SCIPION_SCRIPTS, 'tutorial.py'), sys.argv[2:])

    elif mode in MODE_DEMO:
        runScript(join(SCIPION_SCRIPTS, 'kickoff.py')
                  + ' '.join(sys.argv[2:] if len(sys.argv) > 2 else ''))

    # Allow to run programs from different packages
    # scipion will load the specified environment
    elif (mode.startswith('xmipp') or
          mode.startswith('relion') or
          mode.startswith('e2') or 
          mode.startswith('sx') or
          mode.startswith('b')):
        # To avoid Ghost activation warning
        from pwem import EM_PROGRAM_ENTRY_POINT
        runCmd(EM_PROGRAM_ENTRY_POINT,  sys.argv[1:])

    elif mode == MODE_INSPECT:
        runScript(join(VARS['SCIPION_INSTALL'], 'inspect-plugins.py'), sys.argv[2:])
    # Else HELP or wrong argument
    else:
        sys.stdout.write("""\
Usage: scipion [MODE] [ARGUMENTS]

MODE can be:
    help                   Prints this help message.

    config                 Checks and/or writes Scipion's global and local configuration.
    
    plugins                Launches the plugin manager window.
    
    installp               Installs Scipion plugins from a terminal. Use flag --help to see usage.
    
    uninstallp             Uninstalls Scipion plugins from a terminal. Use with flag --help to see usage.
    
    installb               Installs Plugin Binaries. Use with flag --help to see usage.

    manager                Opens the manager with a list of all projects.

    inspect                inspect a python module and check if it looks loke a scipion plugin. 
    
    printenv               Prints the environment variables used by the application.

    project NAME           Opens the specified project. The name 'last' opens the last project.

    last                   Same as 'project last'

    run COMMAND [ARG ...]  Runs COMMAND within the Scipion environment.
    
    python [ARG ...]       Shortcut for 'scipion run python ...'

    test OPTION            Runs/Lists test(s).
                           OPTION can be:
                             <name>: name of the test to run
                             --show: list the available tests
                             --help: show all the available options
                             --grep <pattern> : filter the list using the <pattern> 
                           For example, to run the "test_object" test:
                             scipion test tests.model.test_object

    testdata OPTION        Gets(puts) tests data, from(to) the server to(from) the $SCIPION_TESTS folder.
                           OPTIONS can be:
                             --download: copy dataset from remote location to local
                             --upload: copy dataset from local to remote
                             <dataset>: name of dataset to download, upload or format
                             --list: list the datasets in the local computer and in the server
                             --help: show all the available options
                           For example, to download the dataset xmipp_tutorial:
                             scipion testdata --download xmipp_tutorial
                           Or to upload it:
                             scipion testdata --upload xmipp_tutorial
                             
    tutorial [NAME]        Creates a new protocol with a tutorial workflow loaded.
                           If NAME is empty, the list of available tutorials are shown.

    view | show NAME       Opens a file with Scipion's showj, or a directory with Browser.
    
    demo | template [PATH] Launches a form based on the *.json.template found either in the PATH
                           or in the pyworkflow/templates directory. If more than one is found,
                           a dialog is raised to choose one. 

""")
        if mode == MODE_HELP:
            sys.exit(0)
        else:
            print("Unknown mode: %s." % mode)
            sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # This way of catching exceptions works with Python 2 & 3
        sys.exit('Error at main: %s\n' % e)
