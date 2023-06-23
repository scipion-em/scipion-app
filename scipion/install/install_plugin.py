# **************************************************************************
# *
# * Authors:     Yaiza Rancel (cyrancel@cnb.csic.es)
# *
# * Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
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

import sys
import argparse
import os
import re

from scipion.constants import MODE_INSTALL_PLUGIN, MODE_UNINSTALL_PLUGIN
from scipion.install import Environment
from scipion.install.plugin_funcs import PluginRepository, PluginInfo, installBinsDefault
from pyworkflow.utils import redStr

#  ************************************************************************
#  *                                                                      *
#  *                       External (EM) Plugins                          *
#  *                                                                      *
#  ************************************************************************
from pyworkflow import Config

MODE_LIST_BINS = 'listb'
MODE_INSTALL_BINS = 'installb'
MODE_UNINSTALL_BINS = 'uninstallb'

# For now let's use scipion hard coded as example for the help
SCIPION_CMD = "scipion"


def installPluginMethods():
    """ Deals with plugin installation methods"""

    # Trigger plugin's variable definition
    Config.getDomain().getPlugins()

    invokeCmd = SCIPION_CMD + " " + sys.argv[1]
    pluginRepo = PluginRepository()

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers(help='mode "%s", "%s" or "listb"' % (MODE_INSTALL_PLUGIN[1], MODE_UNINSTALL_PLUGIN[1]),
                                       dest='mode',
                                       title='Mode',
                                       description='available modes are "%s" or "%s"' % (MODE_INSTALL_PLUGIN[1], MODE_UNINSTALL_PLUGIN[1]))

    ############################################################################
    #                               Install parser                             #
    ############################################################################


    installParser = subparsers.add_parser(MODE_INSTALL_PLUGIN[1], aliases=[MODE_INSTALL_PLUGIN[0]], formatter_class=argparse.RawTextHelpFormatter,
                                          usage="%s  [-h] [--noBin] [-p pluginName [pipVersion ...]]" %
                                                invokeCmd,
                                          epilog="Example: %s -p scipion-em-motioncorr 1.0.6 "
                                                 "-p scipion-em-relion -p scipion-em-eman2 \n\n" %
                                                 invokeCmd,
                                          add_help=False)
    installParser.add_argument('-h', '--help', action='store_true', help='show help')
    installParser.add_argument('--noBin', action='store_true',
                               help='Optional flag to install plugins only as a python module,\n'
                                    'without installing the plugin binaries. This will affect\n'
                                    'all plugins specified in the command.')
    installParser.add_argument('--checkUpdates', action='store_true',
                               help='Optional flag to check which plugins have new releases.\n')
    installParser.add_argument('-p', '--plugin', action='append', nargs='+',
                               metavar=('pluginName', 'pluginVersion'),
                               help='- pluginName:     the name of the plugin to install from the list\n'
                                    '                 of available plugins shown below.\n'
                                    '- pluginVersion: (optional) pip version to install. If not specified,\n'
                                    '                 will install the latest compatible with current Scipion.')

    installParser.add_argument('--devel', action='store_true',
                               help='Optional flag to indicate that we will pass install sources instead\n'
                                    'of pip names. Sources might be local paths or git urls. With local\n'
                                    'paths, will do pip install -e (editable mode). It is expected to find\n'
                                    'the plugin name in the basename of the path or in the repo name. \n'
                                    '(i.e. it needs to match the one specified in setup.py). E.g:\n'
                                    'scipion install -p path/to/pluginName --devel \n'
                                    'scipion install -p https://github.com/someOrg/pluginName.git --devel')
    installParser.add_argument('-j',
                               default='1',
                               metavar='j',
                               help='Number of CPUs to use for compilation \n')

    ############################################################################
    #                             Uninstall parser                             #
    ############################################################################

    uninstallParser = subparsers.add_parser(MODE_UNINSTALL_PLUGIN[1], aliases=[MODE_UNINSTALL_PLUGIN[0]], formatter_class=argparse.RawTextHelpFormatter,
                                            usage="%s  [-h] [-p pluginName [binVersion ...]]" % invokeCmd,
                                            epilog="Example: %s -p scipion-em-eman2 scipion-em-motioncorr \n\n" %
                                                   invokeCmd,
                                            add_help=False)
    uninstallParser.add_argument('-h', '--help', action='store_true', help='show help')
    uninstallParser.add_argument('--noBin', action='store_true',
                                 help='Optional flag to uninstall plugins only as a python module,\n'
                                      'without uninstalling the plugin binaries. This will affect\n'
                                      'all plugins specified in the command.')
    uninstallParser.add_argument('-p', '--plugin', action='append',
                                 metavar='pluginName',
                                 help='The name of the plugin to uninstall from the list\n'
                                      'of available plugins shown below.\n')

    ############################################################################
    #                           Install Bins parser                            #
    ############################################################################

    installBinParser = subparsers.add_parser("installb", formatter_class=argparse.RawTextHelpFormatter,
                                             usage="%s  [-h] binName1 binName2-1.2.3 binName3 ..." % invokeCmd,
                                             epilog="Example: %s ctffind4 eman-2.3\n\n" % invokeCmd,
                                             add_help=False)
    # installBinParser.add_argument('pluginName', metavar='pluginName',
    #                              help='The name of the plugin whose bins we want to uninstall.\n')
    installBinParser.add_argument('-h', '--help', action='store_true', help='show help')
    installBinParser.add_argument('binName', nargs='*',
                                  metavar='binName(s)',
                                  help='The name(s) of the bins we want install, optionally with \n'
                                       'version in the form name-version. If no version is specified,\n'
                                       'will install the last one.')
    installBinParser.add_argument('-j',
                                  default='1',
                                  metavar='j',
                                  help='Number of CPUs to use for compilation \n')

    ############################################################################
    #                          Uninstall Bins parser                           #
    ############################################################################

    uninstallBinParser = subparsers.add_parser("uninstallb", formatter_class=argparse.RawTextHelpFormatter,
                                               usage="%s [-h] binName1 binName2-1.2.3 binName3 ..." % invokeCmd,
                                               epilog="Example: %s ctffind4 relion-3.0\n\n " % invokeCmd,
                                               add_help=False)
    # uninstallBinParser.add_argument('pluginName', metavar='pluginName',
    #                                help='The name of the plugin whose bins we want to uninstall.\n')
    uninstallBinParser.add_argument('-h', '--help', action='store_true', help='show help')
    uninstallBinParser.add_argument('binName', nargs='+',
                                    metavar='binName(s)',
                                    help='The name(s) of the bins we want to uninstall\n'
                                         '(optionally with version in the form name-version). \n'
                                         'If no version is specified, will uninstall the last one.\n')

    modeToParser = {MODE_INSTALL_BINS: installBinParser,
                    MODE_UNINSTALL_BINS: uninstallBinParser,
                    MODE_INSTALL_PLUGIN[0]: installParser,
                    MODE_INSTALL_PLUGIN[1]: installParser,
                    MODE_UNINSTALL_PLUGIN[0]: uninstallParser,
                    MODE_UNINSTALL_PLUGIN[1]: uninstallParser}

    parsedArgs = parser.parse_args(sys.argv[1:])
    mode = parsedArgs.mode
    parserUsed = modeToParser[mode]
    exitWithErrors = False


    if parsedArgs.help or (mode in [MODE_INSTALL_BINS, MODE_UNINSTALL_BINS]
                           and len(parsedArgs.binName) == 0):

        if mode not in [MODE_INSTALL_BINS, MODE_UNINSTALL_BINS]:
            parserUsed.epilog += pluginRepo.printPluginInfoStr()
        else:
            env = Environment()
            env.setDefault(False)
            installedPlugins = Config.getDomain().getPlugins()
            for p, pobj in installedPlugins.items():
                try:
                    pobj.Plugin.defineBinaries(env)
                except Exception as e:
                    print(
                        redStr("Error retrieving plugin %s binaries: " % str(p)), e)
            parserUsed.epilog += env.printHelp()
        parserUsed.print_help()
        parserUsed.exit(0)

    elif mode in MODE_INSTALL_PLUGIN:
        if parsedArgs.checkUpdates:
            print(pluginRepo.printPluginInfoStr(withUpdates=True))
            installParser.exit(0)

        if parsedArgs.devel:
            for p in parsedArgs.plugin:
                pluginSrc = p[0]
                pluginName = ""
                if os.path.exists(pluginSrc):
                    pluginName = os.path.basename(os.path.abspath(pluginSrc).rstrip('/'))
                else:  # we assume it is a git url
                    m = re.match('https://github.com/(.*)/(.*).git', pluginSrc)
                    if m:
                        pluginName = m.group(2)
                if not pluginName:
                    print("ERROR: Couldn't find pluginName for source %s" % pluginSrc)
                    exitWithErrors = True
                else:
                    plugin = PluginInfo(pipName=pluginName, pluginSourceUrl=pluginSrc, remote=False)
                    numberProcessor = parsedArgs.j
                    installed = plugin.installPipModule()
                    if installed and installBinsDefault() and not parsedArgs.noBin:
                        plugin.getPluginClass()._defineVariables()
                        plugin.installBin({'args': ['-j', numberProcessor]})
        else:
            pluginsToInstall = list(zip(*parsedArgs.plugin))[0]
            pluginDict = pluginRepo.getPlugins(pluginList=pluginsToInstall,
                                               getPipData=True)
            if not pluginDict:
                exitWithErrors = True
            else:
                for cmdTarget in parsedArgs.plugin:
                    pluginName = cmdTarget[0]
                    pluginVersion = "" if len(cmdTarget) == 1 else cmdTarget[1]
                    numberProcessor = parsedArgs.j
                    plugin = pluginDict.get(pluginName, None)
                    if plugin:
                        installed = plugin.installPipModule(version=pluginVersion)
                        if installed and installBinsDefault() and not parsedArgs.noBin:
                            plugin.getPluginClass()._defineVariables()
                            plugin.installBin({'args': ['-j', numberProcessor]})
                    else:
                        print("WARNING: Plugin %s does not exist." % pluginName)
                        exitWithErrors = True

    elif parsedArgs.mode in MODE_UNINSTALL_PLUGIN:

        if parsedArgs.plugin:
            for pluginName in parsedArgs.plugin:
                plugin = PluginInfo(pluginName, pluginName, remote=False)
                if plugin.isInstalled():
                    if installBinsDefault() and not parsedArgs.noBin:
                        plugin.uninstallBins()
                    plugin.uninstallPip()
                else:
                    print("WARNING: Plugin %s is not installed." % pluginName)
        else:
            print("Incorrect usage of command 'uninstallp'. Execute 'scipion3 uninstallp --help' or "
                  "'scipion3 help' for more details.")

    elif parsedArgs.mode == MODE_INSTALL_BINS:
        binToInstallList = parsedArgs.binName
        binToPlugin = pluginRepo.getBinToPluginDict()
        for binTarget in binToInstallList:
            pluginTargetName = binToPlugin.get(binTarget, None)
            if pluginTargetName is None:
                print('ERROR: Could not find target %s' % binTarget)
                continue
            pmodule = Config.getDomain().getPlugin(pluginTargetName)
            numberProcessor = parsedArgs.j
            pinfo = PluginInfo(name=pluginTargetName, plugin=pmodule, remote=False)
            pinfo.installBin({'args': [binTarget, '-j', numberProcessor]})

    elif parsedArgs.mode == MODE_UNINSTALL_BINS:

        binToInstallList = parsedArgs.binName
        binToPlugin = pluginRepo.getBinToPluginDict()
        for binTarget in binToInstallList:
            pluginTargetName = binToPlugin.get(binTarget, None)
            if pluginTargetName is None:
                print('ERROR: Could not find target %s' % binTarget)
                continue
            pmodule = Config.getDomain().getPlugin(pluginTargetName)
            pinfo = PluginInfo(name=pluginTargetName, plugin=pmodule, remote=False)
            pinfo.uninstallBins([binTarget])

    if exitWithErrors:
        parserUsed.exit(1)
    else:
        parserUsed.exit(0)
