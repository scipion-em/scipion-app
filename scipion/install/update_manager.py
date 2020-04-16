#!/usr/bin/env python
# **************************************************************************
# *
# * Authors:    J. Jimenez de la Morena (jjimenez@cnb.csic.es)
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

import argparse
import optparse

from pip._internal.commands.list import ListCommand
import pip._internal.utils.misc as piputils
from pip._internal.commands import create_command
from scipion.constants import MODE_UPDATE

Y_COMMAND = '-y'
SCIPION_NAME = 'Scipion'

class UpdateManager:

    pluginName = 'scipion-app'

    @classmethod
    def runUpdateManager(cls, args):
        # create the top-level parser
        parser = argparse.ArgumentParser(prog=args[1:],
                                         formatter_class=argparse.RawTextHelpFormatter)
        subparsers = parser.add_subparsers()
        # create the parser for the "update" command
        parser_f = subparsers.add_parser(MODE_UPDATE,
                                         description='description: update {}.'.format(SCIPION_NAME),
                                         formatter_class=argparse.RawTextHelpFormatter,
                                         usage="{} [-h/--help] [{}]".format(' '.join(args[:2]), Y_COMMAND)
                                         )
        parser_f.add_argument(Y_COMMAND,
                              help='force to update {}.'.format(SCIPION_NAME),
                              action="store_true")

        parsedArgs = parser.parse_args(args[1:])
        if cls.isScipionUpToDate():
            print('{} is up to date.'.format(SCIPION_NAME))
        else:
            print('A new update is available for {}.'.format(SCIPION_NAME))
            if parsedArgs.y:
                cls.updateScipion()
                print('Updating...')
            else:
                answer = input('Would you like to update it now? [Y/n]\n')
                if answer in ['', 'y', 'Y']:
                    cls.updateScipion()
                    print('Updating...')

    @classmethod
    def getUpToDatePluginList(cls):
        return [x.project_name for x in cls.getUpToDatePackages()]

    @classmethod
    def isScipionUpToDate(cls):
        print('Looking for updates...')
        return cls.pluginName in cls.getUpToDatePluginList()

    @classmethod
    def getUpToDatePackages(cls):
        options = optparse.Values({
            'skip_requirements_regex': '',
            'retries': 5, 'pre': False,
            'version': None,
            'include_editable': True,
            'disable_pip_version_check': False,
            'log': None,
            'trusted_hosts': [],
            'outdated': False,
            'no_input': False,
            'local': False,
            'timeout': 15,
            'proxy': '',
            'uptodate': True,
            'help': None,
            'cache_dir': '',
            'no_color': False,
            'user': False,
            'client_cert': None,
            'quiet': 0,
            'not_required': None,
            'no_python_version_warning': False,
            'extra_index_urls': [],
            'isolated_mode': False,
            'exists_action': [],
            'no_index': False,
            'index_url': 'https://pypi.org/simple',
            'find_links': [],
            'path': None,
            'require_venv': False,
            'list_format': 'columns',
            'editable': False,
            'verbose': 0,
            'cert': None})
        distributions = piputils.get_installed_distributions(
            local_only=options.local,
            user_only=options.user,
            editables_only=options.editable,
            include_editables=options.include_editable,
            paths=options.path)
        return cls.genListCommand().get_uptodate(distributions, options)

    @classmethod
    def updateScipion(cls):
        kwargs = {'isolated': False}
        cmd_args = [cls.pluginName,
                    '--upgrade',
                    '-vvv']  # highest level of verbosity

        command = create_command('install', **kwargs)
        status = command.main(cmd_args)
        if status == 0:
            print('Scipion was correctly updated.')
        else:
            print('Something went wrong during the update.')

    @staticmethod
    def genListCommand():
        _args = ()
        _kw = {'summary': 'List installed packages.', 'name': 'list', 'isolated': False}
        return ListCommand(*_args, **_kw)


