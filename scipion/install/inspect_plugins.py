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

    if error:
        error = "ERROR: %s\n" % error

    print("""%s
    Usage: scipion python scripts/inspect_plugins.py [PLUGIN-NAME] [info] [--showBase]
        This script loads all Scipion plugins found.
        If a PLUGIN-NAME is passed, it will inspect that plugin
        in more detail.
        'info' argument will print plugin summary,
        '-showBase' will print Base class protocols (hidden by default).
    """ % error)
    sys.exit(1)


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
        moduleExists = (exists(join(dirname(plugin.__file__), "%s.py" % subName)) or
                        exists(join(dirname(plugin.__file__), subName)))
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
        plugins = Domain.getPlugins()
        print("Plugins:")
        for k, v in plugins.items():
            print("-", k)

        print("Objects")
        pwutils.prettyDict(Domain.getObjects())

        print("Protocols")
        pwutils.prettyDict(Domain.getProtocols())

        print("Viewers")
        pwutils.prettyDict(Domain.getViewers())


    elif n == 2:
        if args[1] in ['-h', '--help', 'help']:
            usage()

        pluginName = args[1]
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

    elif n > 2:
        if args[2] == 'info':
            pluginName = args[1]
            showBase = True if (n == 4 and args[3] == '--showBase') else False
            subclasses = {}
            emCategories = [('Imports', ProtImport),
                            ('Micrographs', ProtMicrographs),
                            ('Particles', ProtParticles),
                            ('2D', Prot2D),
                            ('3D', Prot3D)]

            plugin = Domain.getPlugin(pluginName)
            version = PluginInfo('scipion-em-%s' % pluginName).pipVersion
            bin = PluginInfo('scipion-em-%s' % pluginName).printBinInfoStr()
            print("Plugin name: %s, version: %s" % (pluginName, version))
            print("Plugin binaries: %s" % bin)

            bib, error2 = getSubmodule(plugin, pluginName, 'bibtex')
            if bib is None:
                if error2 is None:
                    msg = " missing bibtex"
                else:
                    exitWithErrors = True
                    msg = ERROR_PREFIX % error2
            else:
                print("Plugin references:")
                bibtex = pwutils.parseBibTex(bib.__doc__)

                for citeStr in bibtex:
                    text = Protocol()._getCiteText(bibtex[citeStr])
                    print(text)

            sub, error = getSubmodule(plugin, pluginName, 'protocols')
            if sub is None:
                if error is None:
                    msg = " missing protocols"
                else:
                    exitWithErrors = True
                    msg = ERROR_PREFIX % error

            else:
                for name in dir(sub):
                    attr = getattr(sub, name)
                    if inspect.isclass(attr) and issubclass(attr, Protocol):
                        # Set this special property used by Scipion
                        attr._package = plugin
                        subclasses[name] = attr

            print("Plugin protocols:\n")
            print("%-35s %-35s %-10s %-s" % (
                'NAME', 'LABEL', 'CATEGORY', 'DESCRIPTION'))

            prots = OrderedDict(sorted(subclasses.items()))
            for prot in prots:
                label = prots[prot].getClassLabel()
                desc = getFirstLine(prots[prot].__doc__)
                cat = 'None'

                for c in emCategories:
                    if issubclass(prots[prot], c[1]):
                        cat = c[0]
                    if prots[prot].isBase():
                        cat = 'Base prot'

                # skip Base protocols if not requested
                if prots[prot].isBase() and not showBase:
                    continue
                else:
                    print("%-35s %-35s %-10s %-s" % (prot, label, cat, desc))

        else:
            usage("The last argument must be 'info'")

    if exitWithErrors:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    inspectPlugin(sys.argv)

