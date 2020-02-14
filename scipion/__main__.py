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
import sys
import os
from os.path import join, exists, dirname, expanduser


import subprocess
from configparser import ConfigParser, ParsingError  # Python 3
from scipion.constants import *
from scipion.utils import (getScipionHome, getInstallPath,
                           getTemplatesPath, getScriptsPath, getPyworkflowPath)
from .scripts.config import getConfigPathFromConfigFile, PROTOCOLS, HOSTS

__version__ = 'v3.0'
__nickname__ = DEVEL
__releasedate__ = ''

# *********************  Helper functions *****************************
def getVersion(long=True):
    if long:
        return "%s (%s) %s" % (__version__, __releasedate__, __nickname__)
    else:
        return __version__


def printVersion():
    """ Print Scipion version """
    # Print the version and some more info
    print('\nScipion %s\n\n' % getVersion())

def config2Dict(configFile, varDict):
    """ Loads a config file if exists and populates a dictionary overwriting the keys """

    # If config file exists
    if exists(configFile):

        #read the file
        config = ConfigParser()
        config.optionxform = str  # keep case (stackoverflow.com/questions/1611799)
        config.read(configFile)

        # For each section
        for sectionName, section in config.items():
            for variable, value in section.items():
                varDict[variable] = value

    return varDict

def envOn(varName):
    value = os.environ.get(varName, '').lower()
    return value in ['1', 'true', 'on', 'yes']


# *********************************************************

# Get Scipion home
scipionHome = getScipionHome()


# ***************** CONFIGURATION  FILES RESOLUTION ************************
# Default values for configuration files.
scipionConfig = join(scipionHome, 'config', 'scipion.conf')
scipionLocalConfig = expanduser(os.environ.get('SCIPION_LOCAL_CONFIG',
                                             '~/.config/scipion/scipion.conf'))

# Allow the user to override them (and remove them from sys.argv).
while len(sys.argv) > 2 and sys.argv[1].startswith('--'):
    arg = sys.argv.pop(1)
    value = sys.argv.pop(1)
    if arg == '--config':
        # If we pass the arguments "--config some_path/scipion.conf",
        # only the config files in that path will be read.
        scipionLocalConfig = scipionConfig = os.path.abspath(os.path.expanduser(value))

        # Verify existence
        if not exists(scipionConfig):
            # Here we can react differently,instead of exiting, may be continuing warning about
            # the missing config file?
            sys.exit('Config file missing: %s' % scipionConfig)

    else:
        sys.exit('Unknown argument: %s' % arg)

# Protocols.conf and hosts.conf, fallback to the template.
protocols = getConfigPathFromConfigFile(scipionConfig, PROTOCOLS)
if not exists(protocols):
    protocols = join(getTemplatesPath(), "protocols.template")

hosts = getConfigPathFromConfigFile(scipionConfig, HOSTS)
if not exists(hosts):
    hosts = join(getTemplatesPath(), "hosts.template")


# *********************** STORE VARIABLES ********************
class Vars:
    """ Class to hold all the variables that are initialized here"""
    SCIPION_DOMAIN = "pwem"

    # Installation paths
    SCIPION_HOME = scipionHome
    # TODO: This, hopefully is a temporary way to load Xmipp binding and it's libraries
    SCIPION_LIBS = join(SCIPION_HOME, "lib")
    os.makedirs(SCIPION_LIBS, exist_ok=True)

    SCIPION_BINDINGS = join(SCIPION_HOME, "bindings")
    os.makedirs(SCIPION_BINDINGS, exist_ok=True)

    # Add bindings to sys.path
    sys.path.append(SCIPION_BINDINGS)

    # Some pw_*.py scripts under 'apps' folder change the current working
    # directory to the SCIPION_HOME, so let's keep the current working
    # directory in case we need it
    SCIPION_CWD = os.path.abspath(os.getcwd())

    # Scipion path to its own scripts
    SCIPION_SCRIPTS = getScriptsPath()
    # Scipion path to install
    SCIPION_INSTALL = getInstallPath()

    # Config files
    SCIPION_CONFIG = scipionConfig
    SCIPION_LOCAL_CONFIG = scipionLocalConfig
    SCIPION_PROTOCOLS = protocols
    SCIPION_HOSTS = hosts

    # Paths to apps or scripts
    PW_APPS = join(getPyworkflowPath(), 'apps')
    SCIPION_TEMPLATES = getTemplatesPath()

    SCIPION_VERSION = getVersion()
    SCIPION_PYTHON = PYTHON
    SCIPION_TESTS_CMD = os.environ.get("SCIPION_TESTS_CMD", '%s %s' % (SCIPION_EP, MODE_TESTS))


# *********************** READ CONFIG FILES ***********************
try:
    VARS = dict()

    # Prepare PYTHON PATH
    ignorePythonPath = os.environ.get('SCIPION_IGNORE_PYTHONPATH', False)
    PYTHONPATH_LIST = [
                       os.environ.get('PYTHONPATH', '') if not ignorePythonPath else "",
                       Vars.SCIPION_BINDINGS,
                       ]

    if 'SCIPION_NOGUI' in os.environ:
        PYTHONPATH_LIST.insert(0, join(getPyworkflowPath(), 'gui', 'no-tkinter'))

    # Load variables from Vars class into VARS dict
    PYTHONPATH = os.pathsep.join(PYTHONPATH_LIST)

    # Load VARS dictionary, all items here will go to the environment
    VARS['PYTHONPATH'] = PYTHONPATH
    VARS['SCIPION_DOMAIN'] = Vars.SCIPION_DOMAIN
    VARS['SCIPION_CONFIG'] = Vars.SCIPION_CONFIG
    VARS['SCIPION_LOCAL_CONFIG'] = Vars.SCIPION_LOCAL_CONFIG
    VARS['SCIPION_PROTOCOLS'] = Vars.SCIPION_PROTOCOLS
    VARS['SCIPION_HOSTS'] = Vars.SCIPION_HOSTS
    VARS['SCIPION_VERSION'] = Vars.SCIPION_VERSION

    # Read main config file
    config2Dict(Vars.SCIPION_CONFIG, VARS)

    # Load the local config
    if Vars.SCIPION_LOCAL_CONFIG != Vars.SCIPION_CONFIG:
        config2Dict(Vars.SCIPION_LOCAL_CONFIG, VARS)

except Exception as e:
    if len(sys.argv) == 1 or sys.argv[1] != MODE_CONFIG:
        print('Error reading config: %s\n' % e)
        print('Please check the configuration file %s and '
                         'try again.\n' % Vars.SCIPION_CONFIG)
        sys.exit(1)

#
# Auxiliary functions to run commands in our environment, one of our
# scripts, or one of our "apps"
#

def runCmd(cmd, args=''):
    """ Runs ANY command with its arguments"""
    if isinstance(args, list):
        args = ' '.join('"%s"' % x for x in args)

    cmd = '%s %s' % (cmd, args)

    os.environ.update(VARS)
    # sys.stdout.write(">>>>> %s\n" % cmd)
    result = os.system(cmd)
    if not -256 < result < 256:
        result = 1  # because if not, 256 is confused with 0 !
    sys.exit(result)


# The following functions require a working SCIPION_PYTHON
def runScript(scriptCmd, args='', chdir=True):
    """"Runs a PYTHON script appending the profiling prefix if ON"""
    if chdir:
        os.chdir(Vars.SCIPION_HOME)

    if envOn('SCIPION_PROFILE'):
        profileStr = '-m cProfile -o output.profile'
    else:
        profileStr = ''
    cmd = '%s %s %s' % (Vars.SCIPION_PYTHON, profileStr, scriptCmd)
    runCmd(cmd, args)


def runApp(app, args='', chdir=True):
    """Runs an app provided by pyworkflow"""
    runScript(join(Vars.PW_APPS, app), args=args, chdir=chdir)


def main():
    printVersion()
    # See in which "mode" the script is called. By default, it's MODE_MANAGER.
    n = len(sys.argv)
    # Default to MANAGER_MODE
    mode = sys.argv[1] if n > 1 else MODE_MANAGER

    # Prepare the environment
    os.environ.update(VARS)

    # Trigger Config initialization once environment is ready
    import pyworkflow
    pwVARS = pyworkflow.Config.getVariableDict()
    VARS.update(pwVARS)

    # Update the environment now with pyworkflow values.
    os.environ.update(VARS)

    # Check mode
    if mode == MODE_MANAGER:

        from pyworkflow.gui.project import ProjectManagerWindow
        ProjectManagerWindow().show()

    elif mode == MODE_LAST:
        os.environ.update(VARS)
        from pyworkflow.apps.pw_project import openProject
        openProject('last')

    elif mode == MODE_HERE:
        os.environ.update(VARS)
        from pyworkflow.apps.pw_project import openProject
        openProject('here')
        
    elif mode == MODE_PROJECT:
        os.environ.update(VARS)
        from pyworkflow.apps.pw_project import openProject
        openProject(sys.argv[2])

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
        os.chdir(Vars.SCIPION_HOME)

        os.environ.update(VARS)
        args = ' '.join(sys.argv)

        runScript('%s %s' % (join(Vars.SCIPION_INSTALL, 'install-plugin.py'), args))

    elif mode == MODE_PLUGINS:
        runScript(join(Vars.SCIPION_INSTALL, PLUGIN_MANAGER_PY))

    elif mode == MODE_CONFIG:
        from .scripts.config import main
        os.environ.update(VARS)
        main(sys.argv[2:])

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
        runApp(join(Vars.SCIPION_SCRIPTS, 'tutorial.py'), sys.argv[2:])

    elif mode in MODE_DEMO:
        from scipion.scripts.kickoff import main as launchKickoff
        # Remove one arg
        sys.argv = sys.argv[1:]
        launchKickoff()

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
        runScript(join(Vars.SCIPION_INSTALL, 'inspect-plugins.py'), sys.argv[2:])
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
