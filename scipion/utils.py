# -*- coding: utf-8 -*
# **************************************************************************
# *
# * Authors: Jorge Jimńenez de la Morena    (jjimenez@cnb.csic.es)
# *
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
from os.path import join, dirname, exists, isdir
from os import environ
import importlib
import importlib.util


def getScipionHome():
    home = environ.get("SCIPION_HOME", None)

    if not home:
        sys.exit("SCIPION_HOME environment variable must be set")

    if not exists(home):
        sys.exit("SCIPION_HOME value (%s) does not exists." % home)

    if not isdir(home):
        sys.exit("SCIPION_HOME value (%s) is not a folder." % home)

    return home


def getScipionAppPath():
    return dirname(__file__)


def getInstallPath():
    return join(getScipionAppPath(), 'install')


def getScriptsPath():
    return join(getScipionAppPath(), 'scripts')


def getTemplatesPath():
    return join(getScipionAppPath(), 'templates')


def getExternalJsonTemplates():
    import pyworkflow
    return dirname(pyworkflow.Config.SCIPION_CONFIG)


def getModuleFolder(moduleName):
    spec = importlib.util.find_spec(moduleName)
    if spec is None:
        raise ModuleNotFoundError(f"Module not found: {moduleName}")

    origin = getattr(spec, "origin", None)
    if origin:
        return dirname(origin)

    searchLocations = getattr(spec, "submodule_search_locations", NonSe)
    if searchLocations:
        for path in searchLocations:
            if path:
                return path

    module = importlib.import_module(moduleName)
    moduleFile = getattr(module, "__file__", None)
    if moduleFile:
        return dirname(moduleFile)

    raise RuntimeError(f"Cannot resolve folder for module: {moduleName}")
