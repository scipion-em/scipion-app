# **************************************************************************
# *
# * Authors: J. Burguet Castell (jburguet@cnb.csic.es)
# *
# * Unidad de Bioinformatica of Centro Nacional de Biotecnologia, CSIC
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
# **************************************************************************
"""
Check the local configuration files, and/or create them if requested
or if they do not exist.
"""
import sys
import os
from datetime import datetime
from os.path import join, exists, basename
import optparse
from pathlib import Path

from configparser import ConfigParser
from shutil import copyfile

from scipion.utils import getTemplatesPath

PYWORKFLOW_SECTION = "PYWORKFLOW"
SCIPION_CONF = 'scipion'
BACKUPS = 'backups'
HOSTS = 'hosts'
MISSING_VAR = "None"
SCIPION_NOTIFY = 'SCIPION_NOTIFY'
SCIPION_CONFIG = 'SCIPION_CONFIG'
SCIPION_LOCAL_CONFIG = 'SCIPION_LOCAL_CONFIG'

UPDATE_PARAM = '--update'
COMPARE_PARAM = '--compare'


def ansi(n):
    """Return function that escapes text with ANSI color n."""
    return lambda txt: '\x1b[%dm%s\x1b[0m' % (n, txt)


black, red, green, yellow, blue, magenta, cyan, white = map(ansi, range(30, 38))


# We don't take them from pyworkflow.utils because this has to run
# with all python versions (and so it is simplified).


def main(args=None):
    parser = optparse.OptionParser(description=__doc__)
    add = parser.add_option  # shortcut
    add('--overwrite', action='store_true',
        help="Rewrite the configuration files using the original templates.")
    add(UPDATE_PARAM, action='store_true',
        help=("Updates you local config files with the values in the template, "
              "only for those missing values."))
    add('--notify', action='store_true',
        help="Allow Scipion to notify usage data (skips user question) "
             "TO BE DEPRECATED, use unattended param instead")
    add('--unattended', action='store_true',
        help="Scipion will skipping questions")
    add('-p', help='Prints the config variables associated to plugin P')

    add(COMPARE_PARAM, action='store_true',
        help="Check that the configurations seems reasonably well set up.")

    add('--show', action='store_true', help="Show the config files used in the default editor")

    options, args = parser.parse_args(args)

    if args:  # no args which aren't options
        sys.exit(parser.format_help())

    unattended = options.notify or options.unattended

    if options.p:
        from pyworkflow import Config
        pluginName = options.p
        plugin = (Config.getDomain().importFromPlugin(pluginName, 'Plugin'))

        if plugin is not None:
            plugin._defineVariables()

            print("Variables defined by plugin '%s':\n" % pluginName)
            for k, v in plugin._vars.items():
                print("%s = %s" % (k, v))
            print("\nThese variables can be added/edited in '%s'"
                  % os.environ[SCIPION_CONFIG])
            url = plugin.getUrl()

            if url != "":
                print("\nMore information these variables might be found at '%s'"
                  % url)

        else:
            print("No plugin found with name '%s'. Module name is expected.\n" % pluginName)

            plugins = Config.getDomain().getPlugins()
            print("\nPlugins available:\n")
            for k in sorted(plugins.keys()):
                print(k)

            print("\nExample: 'scipion3 config -p xmipp3' shows the config variables "
              "defined in 'scipion-em-xmipp' plugin.")

        sys.exit(0)
    elif options.show:
        from pyworkflow.gui.text import _open_cmd
        scipionConf = os.environ[SCIPION_CONFIG]
        homeConf = os.environ[SCIPION_LOCAL_CONFIG]
        _open_cmd(scipionConf)
        if homeConf != scipionConf and os.path.exists(homeConf):
            _open_cmd(os.environ[SCIPION_LOCAL_CONFIG])
        sys.exit(0)
    try:
        # where templates are
        templates_dir = getTemplatesPath()

        scipionConfigFile = os.environ[SCIPION_CONFIG]
        # Global installation configuration files.

        # NOTE: generating a protocols.conf from the template does not make much sense
        # Plugins are dynamically creating sections and the template is currently quite
        # outdated. It doesn't either make sense to update protocols template regularly.
        for fpath, tmplt in [
            (scipionConfigFile, SCIPION_CONF),
            (getConfigPathFromConfigFile(scipionConfigFile, HOSTS), HOSTS)]:
            if not exists(fpath) or options.overwrite:
                print(fpath, tmplt)
                createConf(fpath, join(templates_dir, getTemplateName(tmplt)),
                           unattended=unattended)
            else:
                checkConf(fpath, join(templates_dir, getTemplateName(tmplt)),
                          update=options.update,
                          unattended=unattended)

        # Check paths for the config
        checkPaths(os.environ[SCIPION_CONFIG])

    except Exception as e:
        # This way of catching exceptions works with Python 2 & 3
        print('Config error: %s\n' % e)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def getTemplateName(template):
    return template + '.template'


def checkNotify(config, configfile, unattended):
    """ Check if protocol statistics should be collected. """

    print("""--------------------------------------------------------------
-----------------------------------------------------------------
It would be very helpful if you allow Scipion to send anonymous usage data. This
information will help Scipion's team to identify the more demanded protocols and
prioritize support for them.

Collected usage information is COMPLETELY ANONYMOUS and does NOT include protocol
parameters, files or any data that can be used to identify you or your data. At
https://scipion-em.github.io/docs/docs/developer/collecting-statistics.html you
may see examples of the transmitted data as well as the statistics created with it.
You can always deactivate/activate this option by editing the file %s and setting 
the variable SCIPION_NOTIFY to False/True respectively.

We understand, of course, that you may not wish to have any information collected
from you and we respect your privacy.
""" % configfile)

    if not unattended:
        input("Press <enter> to continue:")

    config.set(PYWORKFLOW_SECTION, SCIPION_NOTIFY, 'True')


def createConf(fpath, ftemplate, unattended=False):
    """Create config file in fpath following the template in ftemplate"""
    # Remove from the template the sections in "remove", and if "keep"
    # is used only keep those sections.

    backup(fpath)

    # Read the template configuration file.
    print(yellow("* Creating configuration file: %s" % fpath))
    print("Please edit it to reflect the configuration of your system.\n")

    # Special case for scipion config
    if getTemplateName(SCIPION_CONF) in ftemplate:

        cf = ConfigParser()
        cf.optionxform = str  # keep case (stackoverflow.com/questions/1611799)

        addPyworkflowVariables(cf)
        addPluginsVariables(cf)

        # Collecting protocol Usage Statistics
        checkNotify(cf, fpath, unattended=unattended)

        # Create the actual configuration file.
        cf.write(open(fpath, 'w'))
    else:
        if not os.path.exists(ftemplate):
            raise FileNotFoundError('Missing file: %s' % ftemplate)

        # For host.conf and protocols.conf, just copy files
        copyfile(ftemplate, fpath)


def backup(fpath):
    """
    Create directory "backup" if necessary and back up the file.

    :param fpath:
    :return: None

    """
    dname = os.path.dirname(fpath)

    if not exists(dname):
        os.makedirs(dname)

    elif exists(fpath):
        if not exists(join(dname, BACKUPS)):
            os.makedirs(join(dname, BACKUPS))
        backupFn = join(dname, BACKUPS,
                      '%s.%s' % (basename(fpath), datetime.now().strftime("%Y%m%d%H%M%S")))
        print(yellow("* Creating backup: %s" % backupFn))
        os.rename(fpath, backupFn)


def addVariablesToSection(cf, section, vars, exclude=[]):
    """ Add all the variables in vars to the config "cf" at the section passed
    it cleans the path to avoid long absolute repetitive paths"""

    def cleanVarPath(varValue):
        """ Clean variable to avoid long paths and relate them to SCIPION_HOME or EM_ROOT"""
        import pwem
        import pyworkflow as pw

        # If it's EM_ROOT, just replace SCIPION_HOME to make it relative
        if varValue == pwem.Config.EM_ROOT:
            varValue = varValue.replace(pwem.Config.SCIPION_HOME, "")
            if varValue.startswith(os.path.sep):
                varValue = varValue[1:]

        elif varValue.startswith(pwem.Config.EM_ROOT):
            varValue = varValue.replace(pwem.Config.EM_ROOT, "%(EM_ROOT)s")

        # duplicate %
        elif "%" in varValue:
            varValue = varValue.replace("%", "%%")

        # If value contains SCIPION_HOME and is not scipion home
        if varValue.startswith(pw.Config.SCIPION_HOME) and varValue != pw.Config.SCIPION_HOME:
            varValue = varValue.replace(pwem.Config.SCIPION_HOME, "${SCIPION_HOME}")

        # Replace HOME paths with ~
        home = str(Path.home())
        if varValue.startswith(home):
            varValue = varValue.replace(home, "~")

        return varValue

    cf.add_section(section)
    for var in sorted(vars.keys()):
        if var not in exclude:
            value = vars[var]
            cf.set(section, var, cleanVarPath(str(value)))


def addPyworkflowVariables(cf):
    # Once more we need a local import to prevent the Config to be wrongly initialized
    import pyworkflow as pw

    exclude = ["SCIPION_CONFIG", "SCIPION_CWD", "SCIPION_LOCAL_CONFIG",
               "SCIPION_HOME", "SCIPION_PROTOCOLS", "SCIPION_HOSTS"]
    # Load pyworkflow variables from the config
    addVariablesToSection(cf, PYWORKFLOW_SECTION, pw.Config.getVars(), exclude)


def addPluginsVariables(cf):
    # Once more we need a local import to prevent the Config to be wrongly initialized
    import pyworkflow as pw
    from pyworkflow.plugin import Plugin

    # Trigger plugin discovery and variable definition
    pw.Config.getDomain().getPlugins()
    addVariablesToSection(cf, "PLUGINS", Plugin.getVars())


def checkPaths(conf):
    """Check that some paths in the config file actually make sense"""

    print("Checking paths in %s ..." % conf)
    cf = ConfigParser()
    cf.optionxform = str  # keep case (stackoverflow.com/questions/1611799)
    assert cf.read(conf) != [], 'Missing file: %s' % conf

    def get(var):
        try:
            return cf.get('BUILD', var)
        except Exception:
            # Not mandatory anymore
            return MISSING_VAR

    allOk = True

    for fname in [join(get('JAVA_BINDIR'), 'java'),
                  get('JAVAC'), get('JAR'),
                  join(get('MPI_BINDIR'), get('MPI_CC')),
                  join(get('MPI_BINDIR'), get('MPI_CXX')),
                  join(get('MPI_BINDIR'), get('MPI_LINKERFORPROGRAMS')),
                  join(get('MPI_INCLUDE'), 'mpi.h')]:
        if not fname.startswith(MISSING_VAR) and not exists(fname):
            print("  Cannot find file: %s" % red(fname))
            allOk = False
    if allOk:
        print(green("All seems fine with %s" % conf))
    else:
        print(red("Errors found."))
        print("Please edit %s and check again." % conf)
        print("To regenerate the config files trying to guess the paths, you "
              "can run: scipion config --overwrite")


def checkConf(fpath, ftemplate, update=False, unattended=False, compare=False):
    """Check that all the variables in the template are in the config file too
    :parameter fpath:  path to the config file
    :parameter ftemplate, template file to compare. Only used for protocols and hosts
    :parameter update: flag, default to false. if true, values from the template will be written to the config file
    :parameter unattended: avoid questions, default to false.
    :parameter compare: make a comparison with the template"""
    # Remove from the checks the sections in "remove", and if "keep"
    # is used only check those sections.

    # Read the config file fpath and the template ftemplate
    cf = ConfigParser(interpolation=None)
    cf.optionxform = str  # keep case (stackoverflow.com/questions/1611799)
    assert cf.read(fpath) != [], 'Missing file %s' % fpath

    ct = ConfigParser(interpolation=None)
    ct.optionxform = str

    suggestUpdate = True  # Flag to suggest --update

    # Special case for scipion config... get values from objects
    if getTemplateName(SCIPION_CONF) in ftemplate:
        # This will be the place to "exclude some variables"
        addPyworkflowVariables(ct)
        addPluginsVariables(ct)
        ftemplate = ":MEMORY:"
    else:
        # Cancel update for others than SCIPION_CONF
        update = False
        suggestUpdate = False
        assert ct.read(ftemplate) != [], 'Missing file %s' % ftemplate

    df = dict([(s, set(cf.options(s))) for s in cf.sections()])
    dt = dict([(s, set(ct.options(s))) for s in ct.sections()])
    # That funny syntax to create the dictionaries works with old pythons.

    if compare:
        compareConfig(cf, ct, fpath, ftemplate)
        return

    confChanged = False

    if df == dt:
        print(green("All the expected sections and options found in " + fpath))
    else:
        print("Found differences between the configuration file\n  %s\n"
              "and the current defined variables.\n  %s" % (fpath, ftemplate))
        sf = set(df.keys())
        st = set(dt.keys())
        for s in sf - st:
            print("Section %s exists in the configuration file but "
                  "not in the template." % red(s))

        for s in st - sf:
            print("Section %s is defined but not in the configuration file. Use %s parameter to update  "
                  "local config files." % (yellow(s), UPDATE_PARAM))

            if update:
                # Update config file with missing section
                cf.add_section(s)
                # add it to the keys
                sf.add(s)
                df[s] = set()
                print("Section %s added to your config file."
                      % green(s))
                confChanged = True

        for s in st & sf:
            for o in df[s] - dt[s]:
                print("In section %s, variable %s exists in the configuration "
                      "file but not defined by any package." % (red(s), red(o)))
            for o in dt[s] - df[s]:
                suggestion = "" if not suggestUpdate else " Use %s parameter to update local config files." % UPDATE_PARAM
                print("In section %s, variable %s is defined by a package but not in the configuration file.%s" % (
                    yellow(s), yellow(o), suggestion))

                if update:
                    if o == 'SCIPION_NOTIFY':
                        checkNotify(ct, fpath, unattended)
                    # Update config file with missing variable
                    value = ct.get(s, o)
                    cf.set(s, o, value)
                    confChanged = True
                    print("Variable %s -> %s added and set to %s in your config file."
                          % (s, green(o), value))

    if update:
        if not confChanged:
            print("Update requested no changes detected for %s." % fpath)
        else:

            print("Changes detected: writing changes into %s.")

            try:
                # Make a back up
                backup(fpath)

                with open(fpath, 'w') as f:
                    cf.write(f)
            except Exception as e:
                print("Could not update the config: ", e)


def compareConfig(cf, ct, fPath, fTemplate):
    """ Compare configuration against template values"""

    print(magenta("COMPARING %s to %s" % (fPath, fTemplate)))
    print(magenta("We expect values to follow the <package>-<version> pattern."
                  " If you see any value not following this pattern please "
                  "update it."))
    # loop through the config
    for s in cf.sections():
        # Get the section
        for variable in cf._sections[s]:
            # Get values
            valueInConfig = getConfigVariable(cf, s, variable)
            valueInTemplate = getConfigVariable(ct, s, variable)

            # Compare value with template
            compareConfigVariable(s, variable, valueInConfig, valueInTemplate)


def getConfigVariable(config, section, variableName):
    return config._sections[section].get(variableName)


def compareConfigVariable(section, variableName, valueInConfig, valueInTemplate):
    if valueInTemplate is None:
        return

    if valueInConfig != valueInTemplate:
        print("%s at %s section (%s) differs from the default value in the "
              "template: %s" % (red(variableName), section, red(valueInConfig),
                                yellow(valueInTemplate)))


def getConfigPathFromConfigFile(scipionConfigFile, configFile):
    """
    :param scipionConfigFile path to the config file to derive the folder name from
    :param configFile: name of the template: protocols or hosts so far
    :return theoretical path for the template at the same path as the config file"""
    return os.path.join(os.path.dirname(scipionConfigFile), configFile + ".conf")


if __name__ == '__main__':
    main()
