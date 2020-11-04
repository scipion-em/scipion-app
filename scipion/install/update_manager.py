#!/usr/bin/env python
# **************************************************************************
# *
# * Authors:    J. Jimenez de la Morena (jjimenez@cnb.csic.es)
# *             Yunior C. Fonseca Reyna (cfonseca@cnb.csic.es)
# *
# *  [1] Unidad de Bioinformatica of Centro Nacional de Biotecnologia, CSIC
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
This module is responsible for updating scipion-em, scipion-pyworkflow and
scipion-app if a higher version of these is released
"""
import argparse
from threading import Thread

from pip._internal.commands import create_command

from pyworkflow.utils import redStr, greenStr, os
from scipion.constants import MODE_UPDATE

DRY_COMMAND = '-dry'
SCIPION_NAME = 'Scipion'


def updateManagerParser(args):
    """
     Create the parser for the "update" command
    """
    parser = argparse.ArgumentParser(prog=args[1:],
                                     formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers()
    parser_f = subparsers.add_parser(MODE_UPDATE,
                                     description='description: update {}.'.format(
                                         SCIPION_NAME),
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     usage="{} [-h/--help] [{}]".format(
                                         ' '.join(args[:2]), DRY_COMMAND)
                                     )
    parser_f.add_argument(DRY_COMMAND,
                          help='only check status {}.'.format(SCIPION_NAME),
                          action="store_true")

    parsedArgs = parser.parse_args(args[1:])
    outdatedPackages = UpdateManager.getPackagesStatus()
    if not outdatedPackages:
        print('{} is up to date.'.format(SCIPION_NAME))
    elif not parsedArgs.dry:
        UpdateManager.updateScipion(outdatedPackages)


class UpdateManager:
    """
    Class responsible for updating scipion-em, scipion-pyworkflow and
    scipion-app if a higher version of these is released
    """
    import pyworkflow
    import pwem
    import scipion

    packageNames = [('scipion-pyworkflow', pyworkflow.__version__),
                    ('scipion-em', pwem.__version__),
                    ('scipion-app', scipion.__version__)]

    @classmethod
    def getPackagesStatus(cls, printAll=True):
        """
        Check for scipion-app, scipion-pyworkflow and scipion-em updates
        return: a list of modules to be updated
        """
        outdatedPackages = []
        for package in cls.packageNames:

            needToUpdate, version = cls.getPackageState(package[0],
                                                        package[1])
            if needToUpdate:
                outdatedPackages.append((package[0], version))
                print(
                    redStr('The package %s is out of date. Your version is %s, '
                           'the latest is %s.' % (package[0], package[1],
                                                  version)))
            elif printAll:
                print(greenStr('The package %s is up to date.  Your version '
                               'is %s' % (package[0], version)))

        return outdatedPackages

    @classmethod
    def getPackageState(cls, packageName, version):
        """
        Check if a package needs to be updated or not
        args: packageName: the package name
              version: version of the installed package
        return: (True, version) if the the package needs to be updated, otherwise
                (False, version)

        """
        # Ignore autocheck of outdated package that happens at import time
        os.environ["OUTDATED_IGNORE"] = "1"
        from outdated import check_outdated
        from requests.exceptions import ConnectionError
        try:
            checkOutdated = check_outdated(packageName, version)
        except ConnectionError as connError:
            print("Cannot check update status of %s (%s)" % (packageName, version))
            return False, version
        except ValueError:
            # We intentionally skip this error
            # When working in devel mode with an increased version not yet release this Value error
            # happens: --> example: Version 3.0.2 is greater than the latest version on PyPI: 3.0.1
            return False, version
        except Exception as ex:
            print(redStr('%s :%s' % (packageName, ex)))
            return False, version

        return checkOutdated

    @classmethod
    def updateScipion(cls, outdatedPackages):
        """
        Update a module from which there is released a higher version
        """
        kwargs = {'isolated': False}

        for packageName in outdatedPackages:
            cmd_args = [packageName[0],
                        '--upgrade',
                        '-vvv']  # highest level of verbosity

            command = create_command('install', **kwargs)
            status = command.main(cmd_args)
            if status == 0:
                print('%s was correctly updated.' % packageName[0])
            else:
                print('Something went wrong during the update of %s.'
                      % packageName[0])
