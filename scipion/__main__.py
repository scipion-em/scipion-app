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
# * the Free Software Foundation; either version 3 of the License, or
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
from os.path import join, exists, expanduser, expandvars

from configparser import ConfigParser
from threading import Thread

from scipion.constants import *
from scipion.utils import (getScipionHome, getInstallPath,
                           getScriptsPath, getTemplatesPath, getModuleFolder)
from scipion.scripts.config import getConfigPathFromConfigFile, HOSTS
from scipion.constants import MODE_UPDATE
from scipion import __version__

__nickname__ = "Eugenius"

# *********************  Helper functions *****************************

def getVersion(long=True):
    if long:
        return "v%s - %s" % (__version__, __nickname__)
    else:
        return __version__


def printVersion():
    """ Print Scipion version """
    # Print the version and some more info
    print('Scipion %s' % getVersion())


def config2Dict(configFile, varDict):
    """ Loads a config file if exists and populates a dictionary
    overwriting the keys.
    """
    # If config file exists
    if exists(configFile):
        # read the file
        config = ConfigParser()
        config.optionxform = str  # keep case (stackoverflow.com/questions/1611799)
        config.read(configFile)

        # For each section
        for sectionName, section in config.items():
            for variable, value in section.items():
                # Expanding user and avoiding comments
                cleanValue = value.split('#')[0]

                # Give priority to environment variables
                varDict[variable] = os.environ.get(variable, default=expandvars(cleanValue).strip())

    return varDict


def envOn(varName):
    value = os.environ.get(varName, '').lower()
    return value in ['1', 'true', 'on', 'yes']


def getMode():
    """ :returns the mode scipion has to be launched """
    return MODE_MANAGER if len(sys.argv) == 1 else sys.argv[1]


# Auxiliary functions to run commands in our environment, one of our
# scripts, or one of our "apps"
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


# ***************** END FUNCTIONS *****************************************

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

        # Verify existence if not config
        if getMode() != MODE_CONFIG and not exists(scipionConfig):
            # Here we can react differently,instead of exiting, may be continuing warning about
            # the missing config file?
            sys.exit('Config file missing: %s' % scipionConfig)

    else:
        sys.exit('Unknown argument: %s' % arg)


hosts = getConfigPathFromConfigFile(scipionConfig, HOSTS)
if not exists(hosts):
    hosts = join(getTemplatesPath(), "hosts.template")


# *********************** STORE VARIABLES ********************
class Vars:
    """ Class to hold all the variables that are initialized here"""
    SCIPION_DOMAIN = "pwem"

    # Installation paths
    SCIPION_HOME = scipionHome

    # Scipion path to its own scripts
    SCIPION_SCRIPTS = getScriptsPath()
    # Scipion path to install
    SCIPION_INSTALL = getInstallPath()

    # Config files
    SCIPION_CONFIG = scipionConfig
    SCIPION_LOCAL_CONFIG = scipionLocalConfig
    SCIPION_HOSTS = os.environ.get('SCIPION_HOSTS', hosts)

    # Paths to apps or scripts
    PW_APPS = join(getModuleFolder("pyworkflow"), 'apps')
    SCIPION_TEMPLATES = getTemplatesPath()

    SCIPION_VERSION = getVersion()
    SCIPION_PYTHON = PYTHON
    SCIPION_TESTS_CMD = os.environ.get("SCIPION_TESTS_CMD", '%s %s' % (SCIPION_EP, MODE_TESTS))

    # Priority package list
    SCIPION_PRIORITY_PACKAGE_LIST = "pwem tomo pwchem"


# *********************** READ CONFIG FILES ***********************
try:
    VARS = dict()

    # Load variables from Vars class into VARS dict

    if 'SCIPION_NOGUI' in os.environ:
        # This cannot work since pyworkflow is not imported and can not be imported here
        # Due to a wrong/early initialisation of the config
        # PYTHONPATH_LIST.insert(0, join(pyworkflow.Config.getPyworkflowPath(), 'gui', 'no-tkinter'))
        print("SCIPION_NOGUI variable not implemented for this version. Please contact us if you need this.")

    # Load VARS dictionary, all items here will go to the environment
    VARS['SCIPION_DOMAIN'] = Vars.SCIPION_DOMAIN
    VARS['SCIPION_CONFIG'] = Vars.SCIPION_CONFIG
    VARS['SCIPION_LOCAL_CONFIG'] = Vars.SCIPION_LOCAL_CONFIG
    VARS['SCIPION_HOSTS'] = Vars.SCIPION_HOSTS
    VARS['SCIPION_VERSION'] = Vars.SCIPION_VERSION
    VARS['SCIPION_PRIORITY_PACKAGE_LIST'] = Vars.SCIPION_PRIORITY_PACKAGE_LIST

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


def main():
    printVersion()
    # See in which "mode" the script is called. By default, it's MODE_MANAGER.
    n = len(sys.argv)
    # Default to MANAGER_MODE
    mode = getMode()

    # Prepare the environment
    os.environ.update(VARS)

    # Set default VIEWERS value for scipion if not defined:
    if not os.environ.get("VIEWERS", None):
        defaultViewers = []
        defaultViewers.append('"Volume":["pwem.viewers.DataViewer"]')
        defaultViewers.append('"VolumeMask":["pwem.viewers.DataViewer"]')
        defaultViewers.append('"SetOfTiltSeries":["imod.viewers.ImodViewer"]')
        defaultViewers.append('"SetOfLandmarkModels":["imod.viewers.ImodViewer"]')
        defaultViewers.append('"SetOfTomograms":["imod.viewers.ImodViewer"]')
        defaultViewers.append('"SetOfSubTomograms":["pwem.viewers.DataViewer"]')
        defaultViewers.append('"SetOfVolumes":["pwem.viewers.DataViewer"]')
        defaultViewers.append('"SetOfParticles":["pwem.viewers.DataViewer"]')

        os.environ["VIEWERS"] = '{%s}' % ','.join(defaultViewers)

    # Trigger Config initialization once environment is ready
    import pyworkflow
    pwVARS = pyworkflow.Config.getVars()
    VARS.update(pwVARS)

    # Update the environment now with pyworkflow values.
    os.environ.update(VARS)

    # Check mode
    if mode == MODE_MANAGER:
        from pyworkflow.gui.project import ProjectManagerWindow
        from scipion.install.update_manager import UpdateManager

        # Check update status in a thread.
        thread = Thread(target=lambda: UpdateManager.getPackagesStatus(printAll=False))
        thread.start()

        ProjectManagerWindow().show()

    elif mode in [MODE_LAST, MODE_HERE, MODE_PROJECT]:
        os.environ.update(VARS)
        from pyworkflow.utils.log import LoggingConfigurator
        LoggingConfigurator.setUpGUILogging()
        from pyworkflow.apps.pw_project import openProject
        arg = sys.argv[2] if mode == MODE_PROJECT else mode
        openProject(arg)

    elif mode == MODE_TESTS or mode == MODE_TEST:
        os.environ.update(VARS)
        from pyworkflow.apps.pw_run_tests import Tester
        Tester().main(sys.argv[2:])

    elif mode == MODE_TEST_DATA:
        os.environ.update(VARS)
        from pyworkflow.apps.pw_sync_data import main
        sys.argv = sys.argv[1:]
        main()

    elif mode in MODE_VIEWER:
        runApp('pw_viewer.py', args=sys.argv[2:], chdir=False)

    # elif mode == MODE_INSTALL_BINS:
    #     runScript('scipion install %s' % ' '.join(sys.argv[2:]))

    elif mode in PLUGIN_MODES:
        os.environ.update(VARS)
        from scipion.install.install_plugin import installPluginMethods
        installPluginMethods()

    elif mode == MODE_PLUGINS:
        os.environ.update(VARS)
        from scipion.install.plugin_manager import PluginManager
        PluginManager("Plugin manager", None).show()

    elif mode == MODE_CONFIG:
        from .scripts.config import main
        os.environ.update(VARS)
        main(sys.argv[2:])

    elif mode == MODE_VERSION:
        # Print main packages version
        import pyworkflow
        import pwem

        print("pyworkflow - %s" % pyworkflow. __version__)
        print("pwem - %s" % pwem.__version__)
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
        from pyworkflow.plugin import Plugin

        # Trigger plugin's variable definition
        pyworkflow.Config.getDomain().getPlugins()
        VARS.update(pyworkflow.plugin.Plugin.getVars())
        for key in sorted(VARS):
            sys.stdout.write('export %s="%s"\n' % (key, VARS[key]))

        sys.exit(0)

    elif mode == MODE_RUN:
        # Run any command with the environment of scipion loaded.
        runCmd('emprogram ' + ' '.join(['"%s"' % arg for arg in sys.argv[2:]]))

    elif mode == MODE_PIP:
        # Runs pip command inside scipion's environment.
        runCmd('pip ' + ' '.join(['"%s"' % arg for arg in sys.argv[2:]]))

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
        runCmd(EM_PROGRAM_ENTRY_POINT, sys.argv[1:])

    elif mode == MODE_INSPECT:
        runScript(join(Vars.SCIPION_INSTALL, 'inspect_plugins.py'), sys.argv[2:])

    elif mode == MODE_UPDATE:
        # Once more: local import to avoid importing pyworkflow, triggered by install.__init__ (Plugin Manager)
        from scipion.install.update_manager import updateManagerParser
        updateManagerParser(sys.argv[:])
    # Else HELP or wrong argument
    else:
        sys.stdout.write("""\
Usage: scipion [--config PATH] [MODE] [ARGUMENTS]

    --config               Full path to a config file.
                    
MODE can be:
    %s                   Prints this help message.

    %s                 Checks and/or writes Scipion's global and local configuration.
    
    %s                Launches the plugin manager window.
    
    %s, %s      Installs Scipion plugins from a terminal. Use flag --help to see usage.
    
    %s, %s  Uninstalls Scipion plugins from a terminal. Use with flag --help to see usage.
    
    %s               Installs Plugin Binaries. Use with flag --help to see usage.
    
    %s             Uninstalls Plugin Binaries. Use with flag --help to see usage.

    %s                Opens the manager with a list of all projects.

    %s                inspect a python module and check if it looks like a scipion plugin. 
    
    %s               Prints the environment variables used by the application.
    
    %s              Displays a list of the available Scipion protocols.
        
    %s [ARGS ...] Run the specified Scipion protocol.

    %s NAME           Opens the specified project. The name 'last' opens the last project.
    
    %s                   Same as 'project last'.

    %s COMMAND [ARG ...]  Runs COMMAND within the Scipion environment.
    
    %s [PIP ARGS ...]     Runs pip within the Scipion environment.
    
    %s [ARG ...]       Shortcut for 'scipion run python ...'.

    %s OPTION            Runs/Lists test(s).
                           OPTION can be:
                             <name>: name of the test to run
                             --show: list the available tests
                             --help: show all the available options
                             --grep <pattern> : filter the list using the <pattern> 
                             --run: run the list off tests. Affected by --grep
                           For example, to run the "test_object" test:
                             scipion test tests.model.test_object

    %s OPTION        Gets(puts) tests data, from(to) the server to(from) the $SCIPION_TESTS folder.
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
                             
    %s                Prints main packages version.
    
    %s | %s        Displays a GUI which allows to run the available Scipion workflow demos. 
    
    %s [NAME]        Creates a new protocol with a tutorial workflow loaded.
                           If NAME is empty, the list of available tutorials are shown.

    %s | %s FILE       Opens a file with Scipion's showj, or a directory with Browser.
    
    %s [TEMPLATE]    Shows all the *.json.template files found in the config folder
                           and all templates provided by plugins. If TEMPLATE 
                           (a path to a template or a template name) is provided, 
                           then that template is used.

    %s [ARGS]          Check for updates of scipion-em, scipion-pyworkflow 
                           and scipion-app and updates them. OPTIONS can be:
                              -h or --help: to see usage.
                              -dry : only check the status of scipion-em, scipion-pyworkflow 
                                     and scipion-app

""" % (MODE_HELP, MODE_CONFIG,
       MODE_PLUGINS,
       MODE_INSTALL_PLUGIN[1], MODE_INSTALL_PLUGIN[0],
       MODE_UNINSTALL_PLUGIN[1], MODE_UNINSTALL_PLUGIN[0],
       MODE_INSTALL_BINS, MODE_UNINSTALL_BINS, MODE_MANAGER, MODE_INSPECT,
       MODE_ENV, MODE_PROTOCOLS, MODE_RUNPROTOCOL, MODE_PROJECT, MODE_LAST,
       MODE_RUN, MODE_PIP, MODE_PYTHON, MODE_TEST, MODE_TEST_DATA, MODE_VERSION,
       MODE_DEMO[0], MODE_DEMO[1], MODE_TUTORIAL, MODE_VIEWER[1], MODE_VIEWER[2],
       MODE_DEMO[1], MODE_UPDATE))

        if mode == MODE_HELP:
            sys.exit(0)
        else:
            print("Unknown mode: %s." % mode)
            sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit('Error at main: %s\n' % e)
