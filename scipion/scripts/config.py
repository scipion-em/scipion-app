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
from os.path import join, exists, basename
import time
import optparse
from pathlib import Path

from configparser import ConfigParser  # Python 3
from shutil import copyfile

from scipion.utils import getTemplatesPath

PYWORKFLOW_SECTION = "PYWORKFLOW"
SCIPION_CONF = 'scipion'
BACKUPS = 'backups'
HOSTS = 'hosts'
PROTOCOLS = 'protocols'
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
        import pyworkflow.utils as pwutils
        pluginName = options.p
        plugin = (pwutils.Config.getDomain().
                  importFromPlugin(pluginName, 'Plugin'))

        if plugin is not None:
            plugin._defineVariables()

            print("Variables defined by plugin '%s':\n" % pluginName)
            for k, v in plugin._vars.items():
                print("%s = %s" % (k, v))
            print("\nThese variables can be added/edited in '%s'"
                  % os.environ[SCIPION_CONFIG])
        else:
            print("No plugin found with name '%s'. Module name is expected,\n"
                  "i.e. 'scipion3 config -p xmipp3' shows the config variables "
                  "defined in 'scipion-em-xmipp' plugin." % pluginName)

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
        for fpath, tmplt in [
            (scipionConfigFile, SCIPION_CONF),
            (getConfigPathFromConfigFile(scipionConfigFile, PROTOCOLS), PROTOCOLS),
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

    # Create directory and backup if necessary.
    dname = os.path.dirname(fpath)
    if not exists(dname):
        os.makedirs(dname)
    elif exists(fpath):
        if not exists(join(dname, BACKUPS)):
            os.makedirs(join(dname, BACKUPS))
        backup = join(dname, BACKUPS,
                      '%s.%d' % (basename(fpath), int(time.time())))
        print(yellow("* Creating backup: %s" % backup))
        os.rename(fpath, backup)

    # Read the template configuration file.
    print(yellow("* Creating configuration file: %s" % fpath))
    print("Please edit it to reflect the configuration of your system.\n")

    if not os.path.exists(ftemplate):
        raise FileNotFoundError('Missing file: %s' % ftemplate)

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
        # For host.conf and protocols.conf, just copy files
        copyfile(ftemplate, fpath)


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
    cf = ConfigParser()
    cf.optionxform = str  # keep case (stackoverflow.com/questions/1611799)
    assert cf.read(fpath) != [], 'Missing file %s' % fpath

    ct = ConfigParser()
    ct.optionxform = str

    suggestUpdate = True  # Flag to suggest --update

    # Special case for scipion config... get values from objects
    if getTemplateName(SCIPION_CONF) in ftemplate:
        # This will be the place to "exclude some variables"
        addPyworkflowVariables(ct)
        addPluginsVariables(ct)
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
              "and the template file\n  %s" % (fpath, ftemplate))
        sf = set(df.keys())
        st = set(dt.keys())
        for s in sf - st:
            print("Section %s exists in the configuration file but "
                  "not in the template." % red(s))

        for s in st - sf:
            print("Section %s exists in the template but not in the configuration file. Use %s parameter to update  "
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
                print("In section %s, option %s exists in the configuration "
                      "file but not in the template." % (red(s), red(o)))
            for o in dt[s] - df[s]:
                suggestion = "" if not suggestUpdate else " Use %s parameter to update local config files." % UPDATE_PARAM
                print("In section %s, option %s exists in the template but not in the configuration file.%s" % (
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
        if confChanged:
            print("Changes detected: writing changes into %s. Please check values." % fpath)
        else:
            print("Update requested no changes detected for %s." % fpath)

        try:
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


def guessJava():
    """Guess the system's Java installation, return a dict with the Java keys"""

    options = {}
    candidates = []

    # First check if the system has a favorite one.
    if 'JAVA_HOME' in os.environ:
        candidates.append(os.environ['JAVA_HOME'])

    # Add also all the ones related to a "javac" program.
    for d in os.environ.get('PATH', '').split(':'):
        if not os.path.isdir(d) or 'javac' not in os.listdir(d):
            continue
        javaBin = os.path.realpath(join(d, 'javac'))
        if javaBin.endswith('/bin/javac'):
            javaHome = javaBin[:-len('/bin/javac')]
            candidates.append(javaHome)
            if javaHome.endswith('/jre'):
                candidates.append(javaHome[:-len('/jre')])

    # Check in order if for any of our candidates, all related
    # directories and files exist. If they do, that'd be our best guess.
    for javaHome in candidates:
        allExist = True
        for path in ['include', join('bin', 'javac'), join('bin', 'jar')]:
            if not exists(join(javaHome, path)):
                allExist = False
        if allExist:
            options['JAVA_HOME'] = javaHome
            break
            # We could instead check individually for JAVA_BINDIR, JAVAC
            # and so on, as we do with MPI options, but we go for an
            # easier and consistent case instead: everything must be under
            # JAVA_HOME, which is the most common case for Java.

    if not options:
        print(red("Warning: could not detect a suitable JAVA_HOME."))
        if candidates:
            print(red("Our candidates were:\n  %s" % '\n  '.join(candidates)))

    return options


def guessMPI():
    """Guess the system's MPI installation, return a dict with MPI keys"""
    # Returns MPI_LIBDIR, MPI_INCLUDE and MPI_BINDIR as a dictionary.

    options = {}
    candidates = []

    # First check if the system has a favorite one.
    for prefix in ['MPI_', 'MPI', 'OPENMPI_', 'OPENMPI']:
        if '%sHOME' % prefix in os.environ:
            candidates.append(os.environ['%sHOME' % prefix])

    # Add also all the ones related to a "mpicc" program.
    for d in os.environ.get('PATH', '').split(':'):
        if not os.path.isdir(d) or 'mpicc' not in os.listdir(d):
            continue
        mpiBin = os.path.realpath(join(d, 'mpicc'))
        if 'MPI_BINDIR' not in options:
            options['MPI_BINDIR'] = os.path.dirname(mpiBin)
        if mpiBin.endswith('/bin/mpicc'):
            mpiHome = mpiBin[:-len('/bin/mpicc')]
            candidates.append(mpiHome)

    # Add some extra directories that are commonly around.
    candidates += ['/usr/lib/openmpi', '/usr/lib64/mpi/gcc/openmpi']

    # Check in order if for any of our candidates, all related
    # directories and files exist. If they do, that'd be our best guess.
    for mpiHome in candidates:
        if (exists(join(mpiHome, 'include', 'mpi.h')) and
                'MPI_INCLUDE' not in options):
            options['MPI_INCLUDE'] = join(mpiHome, 'include')
        if (exists(join(mpiHome, 'lib', 'libmpi.so')) and
                'MPI_LIBDIR' not in options):
            options['MPI_LIBDIR'] = join(mpiHome, 'lib')
        if (exists(join(mpiHome, 'bin', 'mpicc')) and
                'MPI_BINDIR' not in options):
            options['MPI_BINDIR'] = join(mpiHome, 'bin')

    return options


def getConfigPathFromConfigFile(scipionConfigFile, configFile):
    """
    :param scipionConfigFile path to the config file to derive the folder name from
    :param configFile: name of the template: protocols or hosts so far
    :return theoretical path for the template at the same path as the config file"""
    return os.path.join(os.path.dirname(scipionConfigFile), configFile + ".conf")


if __name__ == '__main__':
    main()
