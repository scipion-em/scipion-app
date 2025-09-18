#!/usr/bin/env python
# **************************************************************************
# *
# * Authors:    J. M. De la Rosa Trevin (delarosatrevin@scilifelab.se) [1]
# *             I. Foche Perez (ifoche@cnb.csic.es) [2]
# *             P. Conesa (pconesa@cnb.csic.es) [2]
# *             Y. Fonseca Reyna (cfonseca@cnb.csic.es) [2]
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
import subprocess
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
    print('Scipion %s' % getVersion())


def config2Dict(configFile, varDict):
    """ Loads a config file if exists and populates a dictionary overwriting the keys. """
    if exists(configFile):
        config = ConfigParser()
        config.optionxform = str  # keep case
        config.read(configFile)

        for sectionName, section in config.items():
            for variable, value in section.items():
                cleanValue = value.split('#')[0]
                varDict[variable] = os.environ.get(variable, default=expandvars(cleanValue).strip())
    return varDict


def envOn(varName):
    value = os.environ.get(varName, '').lower()
    return value in ['1', 'true', 'on', 'yes']


def getMode():
    """ Returns the mode scipion has to be launched """
    return MODE_MANAGER if len(sys.argv) == 1 else sys.argv[1]


# *********************** STORE VARIABLES ********************
class Vars:
    """ Class to hold all the variables that are initialized here """
    SCIPION_DOMAIN = "pwem"
    SCIPION_HOME = None
    SCIPION_SCRIPTS = None
    SCIPION_INSTALL = None
    SCIPION_CONFIG = None
    SCIPION_LOCAL_CONFIG = None
    SCIPION_HOSTS = None
    PW_APPS = None
    SCIPION_TEMPLATES = None
    SCIPION_VERSION = None
    SCIPION_PYTHON = PYTHON
    SCIPION_TESTS_CMD = None
    SCIPION_PRIORITY_PACKAGE_LIST = "pwem tomo pwchem"
    VARS = {}

    @classmethod
    def init(cls):
        """ Initialize Vars and configuration. Safe to call from anywhere. """
        scipionHome = getScipionHome()

        # Default config files
        scipionConfig = join(scipionHome, 'config', 'scipion.conf')
        scipionLocalConfig = expanduser(os.environ.get('SCIPION_LOCAL_CONFIG',
                                                       '~/.config/scipion/scipion.conf'))

        # Allow the user to override them (and remove them from sys.argv).
        while len(sys.argv) > 2 and sys.argv[1].startswith('--'):
            arg = sys.argv.pop(1)
            value = sys.argv.pop(1)
            if arg == '--config':
                scipionLocalConfig = scipionConfig = os.path.abspath(os.path.expanduser(value))
                if getMode() != MODE_CONFIG and not exists(scipionConfig):
                    sys.exit('Config file missing: %s' % scipionConfig)
            else:
                sys.exit('Unknown argument: %s' % arg)

        hosts = getConfigPathFromConfigFile(scipionConfig, HOSTS)
        if not exists(hosts):
            hosts = join(getTemplatesPath(), "hosts.template")

        # Initialize attributes
        cls.SCIPION_HOME = scipionHome
        cls.SCIPION_SCRIPTS = getScriptsPath()
        cls.SCIPION_INSTALL = getInstallPath()
        cls.SCIPION_CONFIG = scipionConfig
        cls.SCIPION_LOCAL_CONFIG = scipionLocalConfig
        cls.SCIPION_HOSTS = os.environ.get('SCIPION_HOSTS', hosts)
        cls.PW_APPS = join(getModuleFolder("pyworkflow"), 'apps')
        cls.SCIPION_TEMPLATES = getTemplatesPath()
        cls.SCIPION_VERSION = getVersion()
        cls.SCIPION_TESTS_CMD = os.environ.get("SCIPION_TESTS_CMD",
                                               '%s %s' % (SCIPION_EP, MODE_TESTS))

        # Build VARS dict
        VARS = {}
        if 'SCIPION_NOGUI' in os.environ:
            print("SCIPION_NOGUI variable not implemented for this version. Please contact us if you need this.")

        VARS['SCIPION_DOMAIN'] = cls.SCIPION_DOMAIN
        VARS['SCIPION_CONFIG'] = cls.SCIPION_CONFIG
        VARS['SCIPION_LOCAL_CONFIG'] = cls.SCIPION_LOCAL_CONFIG
        VARS['SCIPION_HOSTS'] = cls.SCIPION_HOSTS
        VARS['SCIPION_VERSION'] = cls.SCIPION_VERSION
        VARS['SCIPION_PRIORITY_PACKAGE_LIST'] = cls.SCIPION_PRIORITY_PACKAGE_LIST

        try:
            config2Dict(cls.SCIPION_CONFIG, VARS)
            if cls.SCIPION_LOCAL_CONFIG != cls.SCIPION_CONFIG:
                config2Dict(cls.SCIPION_LOCAL_CONFIG, VARS)
        except Exception as e:
            if len(sys.argv) == 1 or sys.argv[1] != MODE_CONFIG:
                print('Error reading config: %s\n' % e)
                print('Please check the configuration file %s and try again.\n' % cls.SCIPION_CONFIG)
                sys.exit(1)

        cls.VARS = VARS
        return VARS


# *********************** RUN COMMANDS ****************************
def runCmd(cmd, args=''):
    """ Runs ANY command with its arguments """
    if isinstance(args, list):
        args = ' '.join('"%s"' % x for x in args)
    cmd = '%s %s' % (cmd, args)
    os.environ.update(Vars.VARS)
    result = subprocess.call(cmd, shell=True)
    sys.exit(result)


def runScript(scriptCmd, args='', chdir=True):
    """ Runs a Python script appending the profiling prefix if ON """
    if chdir:
        os.chdir(Vars.SCIPION_HOME)
    profileStr = '-m cProfile -o output.profile' if envOn('SCIPION_PROFILE') else ''
    cmd = '%s %s %s' % (Vars.SCIPION_PYTHON, profileStr, scriptCmd)
    runCmd(cmd, args)


def runApp(app, args='', chdir=True):
    """Runs an app provided by pyworkflow"""
    runScript(join(Vars.PW_APPS, app), args=args, chdir=chdir)


# *********************** CONFIGURE DEFAULT VIEWERS ********************
def configureDefaultViewers():
    """ Initialize default viewers if none are set """
    import pyworkflow
    viewers = pyworkflow.Config.VIEWERS
    if len(viewers) == 0:
        xmippViewer = "pwem.viewers.DataViewer"
        sciViewer = "pwem.viewers.mdviewer.MDViewer"
        imodViewer = "imod.viewers.ImodViewer"
        viewers["Volume"] = [xmippViewer]
        viewers["VolumeMask"] = [xmippViewer]
        viewers["SetOfTiltSeries"] = ["tomo.viewers.AATomoDataViewer"]
        viewers["SetOfLandmarkModels"] = [imodViewer]
        viewers["SetOfTomograms"] = [imodViewer]
        viewers["SetOfTomoMasks"] = [imodViewer]
        viewers["SetOfSubTomograms"] = [sciViewer, xmippViewer]
        viewers["SetOfVolumes"] = [sciViewer, xmippViewer]
        viewers["SetOfParticles"] = [sciViewer, xmippViewer]
        viewers["SetOfCoordinates3D"] = ["emantomo.viewers.EmanDataViewer", "dynamo.viewers.DynamoDataViewer"]
        viewers["SetOfCoordinates"] = [xmippViewer]
        viewers["SetOfMeshes"] = ["dynamo.viewers.DynamoDataViewer"]
        viewers["SetOfFSCs"] = ["pwem.viewers.FscViewer"]
        var = pyworkflow.VariablesRegistry._variables["VIEWERS"]
        var.default = viewers
        var.value = viewers


# *********************** MODE HANDLERS ****************************
def handleHelpMode():
    """ Prints help message """
    handleUnknownMode()


def handleUnknownMode():
    """ Prints usage and exits """
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

        %s [NAME]        Creates a new protocol with a tutorial workflow loaded.
                               If NAME is empty, the list of available tutorials are shown.

        %s | %s FILE       Opens a file with Scipion's showj, or a directory with Browser.

        %s -h            Shows help for launching templates               

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
           MODE_TUTORIAL, MODE_VIEWER[1], MODE_VIEWER[2],
           MODE_DEMO[1], MODE_UPDATE))
    sys.exit(0)


def handleManagerMode():
    from pyworkflow.gui.project import ProjectManagerWindow
    from scipion.install.update_manager import UpdateManager
    thread = Thread(target=lambda: UpdateManager.getPackagesStatus(printAll=False))
    thread.start()
    ProjectManagerWindow().show()


def handleProjectMode():
    from pyworkflow.apps.pw_project import openProject
    mode = getMode()
    if mode == MODE_PROJECT:
        arg = sys.argv[2] if len(sys.argv) == 3 else "list"
    else:
        arg = mode
    openProject(arg)


def handleTestsMode():
    from pyworkflow.apps.pw_run_tests import Tester
    Tester().main(sys.argv[2:])


def handleTestDataMode():
    from pyworkflow.apps.pw_sync_data import main
    sys.argv = sys.argv[1:]
    main()


def handleViewerMode():
    runApp('pw_viewer.py', args=sys.argv[2:], chdir=False)


def handlePluginsWindowMode():
    from pyworkflow.utils import LoggingConfigurator
    LoggingConfigurator.setupLogging(consoleLevel=None)
    from scipion.install.plugin_manager import PluginManager
    PluginManager("Plugin manager", None).show()


def handlePluginsMode():
    from pyworkflow.utils import LoggingConfigurator
    LoggingConfigurator.setupLogging()
    from scipion.install.install_plugin import installPluginMethods
    installPluginMethods()


def handleConfigMode():
    from .scripts.config import main
    os.environ.update(Vars.VARS)
    main(sys.argv[2:])


def handleVersionMode():
    import pyworkflow
    import pwem
    print("pyworkflow - %s" % pyworkflow.__version__)
    print("pwem - %s" % pwem.__version__)
    sys.exit(0)


def handleRunProtocolMode():
    n = len(sys.argv)
    assert (n == 6 or n == 7), 'runprotocol takes exactly 5 arguments, not %d' % (n - 1)
    protocolApp = sys.argv[2]
    runApp(protocolApp, args=sys.argv[3:])


def handleProtocolsMode():
    runApp('pw_protocol_list.py', args=sys.argv[2:])


def handleEnvMode():
    import pyworkflow
    from pyworkflow.utils import greenStr, yellowStr
    pyworkflow.Config.getDomain().getPlugins()
    for key, var in pyworkflow.VariablesRegistry.variables().items():
        sys.stdout.write('%s="%s"\n' % (key, var.value))
        if len(sys.argv) > 2:
            if var.description is not None:
                sys.stdout.write(greenStr(var.description + "\n"))
            sys.stdout.write(yellowStr("SOURCE: %s\n" % var.source))
    sys.exit(0)


def handleRunMode():
    runCmd('emprogram ' + ' '.join(['"%s"' % arg for arg in sys.argv[2:]]))


def handlePipMode():
    runCmd('pip ' + ' '.join(['"%s"' % arg for arg in sys.argv[2:]]))


def handlePythonMode():
    runScript(' '.join(['"%s"' % arg for arg in sys.argv[2:]]), chdir=False)


def handleTutorialMode():
    runApp(join(Vars.SCIPION_SCRIPTS, 'tutorial.py'), sys.argv[2:])


def handleDemoMode():
    from scipion.scripts.kickoff import main as launchKickoff
    sys.argv = sys.argv[1:]
    launchKickoff()


def handleUpdateMode():
    from scipion.install.update_manager import updateManagerParser
    updateManagerParser(sys.argv[:])


def handleInspectMode():
    from scipion.install.inspect_plugins import inspectPlugin
    inspectPlugin(sys.argv[1:])


# *********************** MAP MODES TO HANDLERS ****************************
MODE_HANDLERS = {
    MODE_HELP: handleHelpMode,
    MODE_MANAGER: handleManagerMode,
    MODE_PROJECT: handleProjectMode,
    MODE_LAST: handleProjectMode,
    MODE_HERE: handleProjectMode,
    MODE_TESTS: handleTestsMode,
    MODE_TEST: handleTestsMode,
    MODE_TEST_DATA: handleTestDataMode,
    MODE_VIEWER[0]: handleViewerMode,
    MODE_VIEWER[1]: handleViewerMode,
    MODE_VIEWER[2]: handleViewerMode,
    MODE_PLUGINS: handlePluginsWindowMode,
    MODE_INSTALL_PLUGIN[0]: handlePluginsMode,
    MODE_INSTALL_PLUGIN[1]: handlePluginsMode,
    MODE_UNINSTALL_PLUGIN[0]: handlePluginsMode,
    MODE_UNINSTALL_PLUGIN[1]: handlePluginsMode,
    MODE_UNINSTALL_BINS: handlePluginsMode,
    MODE_INSTALL_BINS: handlePluginsMode,
    MODE_CONFIG: handleConfigMode,
    MODE_VERSION: handleVersionMode,
    MODE_RUNPROTOCOL: handleRunProtocolMode,
    MODE_PROTOCOLS: handleProtocolsMode,
    MODE_ENV: handleEnvMode,
    MODE_RUN: handleRunMode,
    MODE_PIP: handlePipMode,
    MODE_PYTHON: handlePythonMode,
    MODE_TUTORIAL: handleTutorialMode,
    MODE_DEMO[1]: handleDemoMode,
    MODE_UPDATE: handleUpdateMode,
    MODE_INSPECT: handleInspectMode
}


# *********************** MAIN ENTRY POINT ****************************
def main():
    printVersion()
    Vars.init()  # Initialize all variables and configs
    os.environ.update(Vars.VARS)

    # Load pyworkflow and configure default viewers
    configureDefaultViewers()

    # Treat '--help' or '-h' as a special mode
    if len(sys.argv) > 1 and sys.argv[1] in ('--help', '-h'):
        mode = MODE_HELP
    else:
        mode = getMode()

    # Call the corresponding handler
    handler = MODE_HANDLERS.get(mode, handleUnknownMode)
    handler()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit('Error at main: %s\n' % e)
