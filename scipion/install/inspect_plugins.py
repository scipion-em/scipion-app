#!/usr/bin/env python
# **************************************************************************
# *
# * Authors:     J.M. De la Rosa Trevin (delarosatrevin@scilifelab.se) [1]
# *
# * [1] SciLifeLab, Stockholm University
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
from os.path import join, exists, dirname
import importlib
import inspect
import traceback
from collections import OrderedDict

from pwem.protocols import (Prot3D, Prot2D, ProtParticles,
                            ProtMicrographs, ProtImport)
from pwem import Domain
from pyworkflow.protocol import Protocol
import pyworkflow.utils as pwutils

from scipion.install.plugin_funcs import PluginInfo

ERROR_PREFIX = " error -> %s"

def usage(error=""):

    exitCode =0
    if error:
        error = "ERROR: %s\n" % error
        exitCode = 1

    print("""%s
    Usage: scipion3 python -m scipion.install.inspect_plugins [h]|[all]|[PLUGIN-NAME] [info] [--showBase]
        
        Without parameters this will show the list of avaialble plugins.
        
        With 'all' will print all objects discovered (protocols, viewers, wizards, objects)
        
        With 'h' will print this help maessage.
        
        If a PLUGIN-NAME is passed, it will inspect that plugin
        in more detail. Useful to discover loading time errors of the plugin.
        
          - 'info' argument will print plugin summary of the plugin,
          - '-showBase' will print Base class protocols (hidden by default).
        
    """ % error)
    sys.exit(exitCode)


def getSubmodule(plugin, name, subname):
    """ Return a tuple: (module, error)
    If module is None:
        1) if error is None is that the submodule does not exist
        2) if error is not None, it is an Exception raised when
        importing the submodule
    """

    try:
        m = importlib.import_module('%s.%s' % (name, subname))
        r = (m, None)
    except Exception as e:
        noModuleMsg = 'No module named \'%s.%s\'' % (name, subname)
        msg = str(e)
        moduleExists = (exists(join(dirname(plugin.__file__), "%s.py" % subname)) or
                        exists(join(dirname(plugin.__file__), subname)))
        r = (None, None if msg == noModuleMsg and not moduleExists else traceback.format_exc())
    return r


def getFirstLine(doc):
    """ Get the first non-empty line from doc. """
    if doc:
        for lines in doc.split('\n'):
            l = lines.strip()
            if l:
                return l
    return ''


def inspectPlugin(args):

    exitWithErrors = False

    n = len(args)

    if n > 4:
        usage("Incorrect number of input parameters")

    if n == 1:  # List all plugins
        printPlugins()

    elif n == 2:
        firstArg = args[1]
        if firstArg in ['-h', 'h', '--help', 'help']:
            usage()

        elif firstArg in ['all', '-all', '--all']:
            listAllPlugins()

        pluginName = args[1]
        exitWithErrors = showPluginInfo(exitWithErrors, pluginName)

    elif n > 2:

        exitWithErrors = showInfo(args, exitWithErrors, n)

    if exitWithErrors:
        sys.exit(1)
    else:
        sys.exit(0)


def showPluginInfo(exitWithErrors, pluginName):
    plugin = Domain.getPluginModule(pluginName)
    print("Plugin: %s" % pluginName)
    for subName in ['constants', 'convert', 'protocols',
                    'wizards', 'viewers', 'tests']:
        sub, error = getSubmodule(plugin, pluginName, subName)

        if sub is None:
            if error is None:
                msg = " missing"
            else:
                exitWithErrors = True
                msg = ERROR_PREFIX % error

        else:
            msg = " loaded"

        print("   >>> %s: %s" % (subName, msg))
    return exitWithErrors


def showInfo(args, anyError, n):

    pluginName = args[1]
    showBase = True if (n == 4 and args[3] == '--showBase') else False
    plugin = Domain.getPluginModule(pluginName)
    pluginInfo = PluginInfo('scipion-em-%s' % pluginName)
    version = pluginInfo.pipVersion
    bin = pluginInfo.printBinInfoStr()
    print("Plugin name: %s, version: %s" % (pluginName, version))
    print("Plugin binaries: %s" % bin)

    anyError = showReferences(anyError, plugin, pluginName)

    anyError = showProtocols(anyError, plugin, pluginName, showBase)

    return anyError


def showProtocols(anyError, plugin, pluginName, showBase):

    subclasses=dict()

    sub, error = getSubmodule(plugin, pluginName, 'protocols')
    if sub is None:
        anyError = error is not None

    else:
        for name in dir(sub):
            attr = getattr(sub, name)
            if inspect.isclass(attr) and issubclass(attr, Protocol):
                # Set this special property used by Scipion
                attr._package = plugin
                attr._plugin = plugin.Plugin()

                subclasses[name] = attr
    print("Plugin protocols:\n")
    print("%-35s %-35s %-s" % (
        'NAME', 'LABEL', 'DESCRIPTION'))
    prots = OrderedDict(sorted(subclasses.items()))
    for prot in prots:
        label = prots[prot].getClassLabel()
        desc = getFirstLine(prots[prot].__doc__)

        # skip Base protocols if not requested
        if prots[prot].isBase() and not showBase:
            continue
        else:
            print("%-35s %-35s %-s" % (prot, label, desc))
    return anyError


def showReferences(anyError, plugin, pluginName):
    bib, error2 = getSubmodule(plugin, pluginName, 'bibtex')
    if bib is None:
        anyError = error2 is not None
    else:
        print("Plugin references:")
        bibtex = pwutils.parseBibTex(bib.__doc__)

        for citeStr in bibtex:
            text = Protocol()._getCiteText(bibtex[citeStr])
            print(text)
    return anyError

def printPlugins():
    """ Print all plugins found found """
    plugins = Domain.getPlugins()
    print("Plugins:")
    print("scipion3 inspect <plugin-name-bellow> for a more detailed information about the plugin")
    for k, v in plugins.items():
        print("-", k)

def listAllPlugins():

    printPlugins()

    print("Objects")
    pwutils.prettyDict(Domain.getObjects())

    print("Protocols")
    pwutils.prettyDict(Domain.getProtocols())

    print("Viewers")
    pwutils.prettyDict(Domain.getViewers())

    sys.exit(0)


if __name__ == '__main__':
    inspectPlugin(sys.argv)

