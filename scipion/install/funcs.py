# **************************************************************************
# *
# * Authors: J.M. De la Rosa Trevin (delarosatrevin@scilifelab.se) [1]
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
import logging

from pyworkflow.utils import redStr

logger = logging.getLogger(__name__)
import os
import platform
import sys
import time
from glob import glob
from os.path import join, exists, islink, abspath
from subprocess import STDOUT, call

from pyworkflow import Config
import pwem
from typing import List, Tuple, Dict


# Then we get some OS vars
MACOSX = (platform.system() == 'Darwin')
WINDOWS = (platform.system() == 'Windows')
LINUX = (platform.system() == 'Linux')
VOID_TGZ = "void.tgz"


def ansi(n):
    """Return function that escapes text with ANSI color n."""
    return lambda txt: '\x1b[%dm%s\x1b[0m' % (n, txt)


black, red, green, yellow, blue, magenta, cyan, white = map(ansi, range(30, 38))


# We don't take them from pyworkflow.utils because this has to run
# with all python versions (and so it is simplified).


def progInPath(prog):
    """ Is program prog in PATH? """
    for base in os.environ.get('PATH', '').split(os.pathsep):
        if exists('%s/%s' % (base, prog)):
            return True
    return False


def checkLib(lib, target=None):
    """ See if we have library lib """
    try:
        ret = call(['pkg-config', '--cflags', '--libs', lib],
                   stdout=open(os.devnull, 'w'), stderr=STDOUT)
        if ret != 0:
            raise OSError
        return True
    except OSError:
        try:
            ret = call(['%s-config' % lib, '--cflags'])
            if ret != 0:
                raise OSError
            return True
        except OSError:
            return False


class Command:
    def __init__(self, env, cmd, targets=None, **kwargs):
        self._env = env
        self._cmd = cmd

        if targets is None:
            self._targets = []
        elif isinstance(targets, str):
            self._targets = [targets]
        else:
            self._targets = targets

        self._cwd = kwargs.get('cwd', None)
        self._out = kwargs.get('out', None)
        self._always = kwargs.get('always', False)
        self._environ = kwargs.get('environ', None)

    def _existsAll(self):
        """ Return True if all targets exist. """
        for t in self._targets:
            if not glob(t):
                return False
        return True

    def execute(self):
        if not self._always and self._targets and self._existsAll():
            print("  Skipping command: %s" % cyan(self._cmd))
            print("  All targets %s exist." % self._targets)
        else:
            cwd = os.getcwd()
            if self._cwd is not None:
                if not self._env.showOnly:
                    os.chdir(self._cwd)
                print(cyan("cd %s" % self._cwd))

            # Actually allow self._cmd to be a list or a
            # '\n'-separated list of commands, and run them all.
            if isinstance(self._cmd, str):
                cmds = self._cmd.split('\n')  # create list of commands
            elif callable(self._cmd):
                cmds = [self._cmd]  # a function call
            else:
                cmds = self._cmd  # already a list of whatever

            for cmd in cmds:
                if self._out is not None:
                    cmd += ' > %s 2>&1' % self._out
                    # TODO: more general, this only works for bash.

                print(cyan(cmd))

                if self._env.showOnly:
                    continue  # we don't really execute the command here

                if callable(cmd):  # cmd could be a function: call it
                    cmd()
                else:  # if not, it's a command: make a system call
                    call(cmd, shell=True, env=self._environ,
                         stdout=sys.stdout, stderr=sys.stderr)

            # Return to working directory, useful when we change dir
            # before executing the command.
            os.chdir(cwd)
            if not self._env.showOnly:
                for t in self._targets:
                    if not glob(t):
                        print(red("ERROR: File or folder '%s' not found after running '%s'." % (t, cmd)))
                        sys.exit(1)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "Command: %s, targets: %s" % (self._cmd, self._targets)


class Target:
    def __init__(self, env, name, *commands, **kwargs):
        self._env = env
        self._name = name
        self._default = kwargs.get('default', False)
        self._always = kwargs.get('always', False)  # Adding always here to allow getting to Commands where always=True
        self._commandList = list(commands)  # copy the list/tuple of commands
        self._finalCommands = []  # their targets will be used to check if we need to re-build
        self._deps = []  # names of dependency targets

    def getCommands(self):
        return self._commandList

    def addCommand(self, cmd, **kwargs):
        if isinstance(cmd, Command):
            c = cmd
        else:
            c = Command(self._env, cmd, **kwargs)
        self._commandList.append(c)

        if kwargs.get('final', False):
            self._finalCommands.append(c)
        return c

    def addDep(self, dep):
        self._deps.append(dep)

    def getDeps(self):
        return self._deps

    def _existsAll(self):
        for c in self._finalCommands:
            if not c._existsAll():
                return False
        return True

    def isDefault(self):
        return self._default

    def setDefault(self, default):
        self._default = default

    def getName(self):
        return self._name

    def execute(self):
        t1 = time.time()

        print(green("Installing %s ..." % self._name))
        if not self._always and self._existsAll():
            print("  All targets exist, skipping.")
        else:
            for command in self._commandList:
                command.execute()

        if not self._env.showOnly:
            dt = time.time() - t1
            if dt < 60:
                print(green('Done (%.2f seconds)' % dt))
            else:
                print(green('Done (%d m %02d s)' % (dt / 60, int(dt) % 60)))

    def __str__(self):
        return "Name: %s, default: %s, always: %s, commands: %s, final commands: %s, deps: %s." %(
            self._name, self._default, self._always,
            self._commandList,self._finalCommands, self._deps)



class Environment:

    def __init__(self, **kwargs):
        self._targetDict = {}
        self._targetList = []
        # We need a targetList which has the targetDict.keys() in order
        # (OrderedDict is not available in python < 2.7)

        self._packages = {}  # dict of available packages (to show in --help)

        self._args = kwargs.get('args', [])
        self.showOnly = '--show' in self._args

        # Find if the -j arguments was passed to get the number of processors
        if '-j' in self._args:
            j = self._args.index('-j')
            self._processors = int(self._args[j + 1])
        else:
            self._processors = 1

        if LINUX:
            self._libSuffix = 'so'  # Shared libraries extension name
        else:
            self._libSuffix = 'dylib'

        self._downloadCmd = ('wget -nv -c -O %(tar)s.part %(url)s\n'
                             'mv -v %(tar)s.part %(tar)s')
        # Removed the z: "The tar command auto-detects compression type and extracts the archive"
        # From https://linuxize.com/post/how-to-extract-unzip-tar-bz2-file/#extracting-tarbz2-file
        self._tarCmd = 'tar -xf %s'
        self._pipCmd = kwargs.get('pipCmd', 'pip install %s==%s')

    def getLibSuffix(self):
        return self._libSuffix

    def getProcessors(self):
        return self._processors

    @staticmethod
    def getSoftware(*paths):
        return os.path.join(Config.SCIPION_SOFTWARE, *paths)

    @staticmethod
    def getLibFolder(*paths):
        return Environment.getSoftware("lib", *paths)

    @staticmethod
    def getPython():
        return sys.executable

    # Pablo: A quick search didn't find usages.
    # @staticmethod
    # def getPythonFolder():
    #     return Environment.getLibFolder() + '/python2.7'

    @staticmethod
    def getPythonPackagesFolder():
        # This does not work on MAC virtual envs
        # import site
        # return site.getsitepackages()[0]

        from sysconfig import get_paths
        return get_paths()["purelib"]

    @staticmethod
    def getIncludeFolder():
        return Environment.getSoftware('include')

    def getLib(self, name):

        return Environment.getLibFolder('lib%s.%s' % (name, self._libSuffix))

    @staticmethod
    def getBinFolder(*paths):
        return os.path.join(mkdir(Environment.getSoftware('bin')), *paths)

    @staticmethod
    def getBin(name):
        return Environment.getBinFolder(name)

    @staticmethod
    def getTmpFolder():
        return mkdir(Environment.getSoftware('tmp'))

    @staticmethod
    def getLogFolder(*path):
        return os.path.join(mkdir(Environment.getSoftware('log')), *path)

    @staticmethod
    def getEmFolder():
        return mkdir(pwem.Config.EM_ROOT)

    @staticmethod
    def getEm(name):
        return '%s/%s' % (Environment.getEmFolder(), name)

    def getTargetList(self):
        return self._targetList

    def addTarget(self, name, *commands, **kwargs):

        if name in self._targetDict:
            raise Exception("Duplicated target '%s'" % name)

        t = Target(self, name, *commands, **kwargs)
        self._targetList.append(t)
        self._targetDict[name] = t

        return t

    def addTargetAlias(self, name, alias):
        """ Add an alias to an existing target.
        This function will be used for installing the last version of each
        package.
        """
        if name not in self._targetDict:
            raise Exception("Can't add alias, target name '%s' not found. "
                            % name)

        self._targetDict[alias] = self._targetDict[name]

    def getTarget(self, name):
        return self._targetDict[name]

    def hasTarget(self, name):
        return name in self._targetDict

    def getTargets(self):
        return self._targetList

    def _addTargetDeps(self, target, deps):
        """ Add the dependencies to target.
        Check that each dependency correspond to a previous target.
        """
        for d in deps:
            if isinstance(d, str):
                targetName = d
            elif isinstance(d, Target):
                targetName = d.getName()
            else:
                raise Exception("Dependencies should be either string or "
                                "Target, received: %s" % d)

            if targetName not in self._targetDict:
                raise Exception("Dependency '%s' does not exists. " % targetName)

            target.addDep(targetName)

    def _addDownloadUntar(self, name, **kwargs):
        """ Build a basic target and add commands for Download and Untar.
        This is the base for addLibrary, addModule and addPackage.

        :param createBuildDir:  If true tar extraction will specify an extraction dir. Use this for plain tgz, tars, ...use with target

        """
        # Use reasonable defaults.
        tar = kwargs.get('tar', '%s.tgz' % name)
        urlSuffix = kwargs.get('urlSuffix', 'external')
        url = kwargs.get('url', '%s/%s/%s' % (Config.SCIPION_URL_SOFTWARE, urlSuffix, tar))
        downloadDir = kwargs.get('downloadDir', self.getTmpFolder())
        buildDir = self._getBuildDir(kwargs, tar)
        targetDir = kwargs.get('targetDir', buildDir)

        createBuildDir = kwargs.get('createBuildDir', False)

        deps = kwargs.get('deps', [])

        # Download library tgz
        tarFile = join(downloadDir, tar)
        buildPath = join(downloadDir, buildDir)
        targetPath = join(downloadDir, targetDir)

        t = self.addTarget(name, default=kwargs.get('default', True))
        self._addTargetDeps(t, deps)
        t.buildDir = buildDir
        t.buildPath = buildPath
        t.targetPath = targetPath

        # check if tar exists and has size >0 so that we can download again
        if os.path.isfile(tarFile) and os.path.getsize(tarFile) == 0:
            os.remove(tarFile)

        if url.startswith('file:'):
            t.addCommand('ln -s %s %s' % (url.replace('file:', ''), tar),
                         targets=tarFile,
                         cwd=downloadDir)
        else:
            t.addCommand(self._downloadCmd % {'tar': tarFile, 'url': url},
                         targets=tarFile)


        tarCmd = self._tarCmd % tar

        # If we need to create the build dir (True)
        if createBuildDir:

            # If is the void one, just mkdir. DO not extract anything
            if tar == VOID_TGZ:
                tarCmd = 'mkdir %s' % buildPath
            else:
                tarCmd = 'mkdir {0} && {1} -C {2}'.format(buildPath,tarCmd, buildDir)

        finalTarget = join(downloadDir, kwargs.get('target', buildDir))
        t.addCommand(tarCmd,
                     targets=finalTarget,
                     cwd=downloadDir)

        logger.debug("Target added: %s" % t)

        return t

    def addLibrary(self, name, **kwargs):
        """Add library <name> to the construction process.

        Checks that the needed programs are in PATH, needed libraries
        can be found, downloads the given url, untars the resulting
        tar file, configures the library with the given flags,
        compiles it (in the given buildDir) and installs it.

        If default=False, the library will not be built.

        Returns the final targets, the ones that Make will create.

        """
        configTarget = kwargs.get('configTarget', 'Makefile')
        configAlways = kwargs.get('configAlways', False)
        flags = kwargs.get('flags', [])
        targets = kwargs.get('targets', [self.getLib(name)])
        clean = kwargs.get('clean', False)  # Execute make clean at the end??
        cmake = kwargs.get('cmake', False)  # Use cmake instead of configure??
        default = kwargs.get('default', True)
        neededProgs = kwargs.get('neededProgs', [])
        libChecks = kwargs.get('libChecks', [])

        if default or name in sys.argv[2:]:
            # Check that we have the necessary programs and libraries in place.
            for prog in neededProgs:
                assert progInPath(prog), ("Cannot find necessary program: %s\n"
                                          "Please install and try again" % prog)
            for lib in libChecks:
                checkLib(lib)

        # If passing a command list (of tuples (command, target)) those actions
        # will be performed instead of the normal ./configure / cmake + make
        commands = kwargs.get('commands', [])

        t = self._addDownloadUntar(name, **kwargs)
        configDir = kwargs.get('configDir', t.buildDir)

        configPath = join(self.getTmpFolder(), configDir)
        makeFile = '%s/%s' % (configPath, configTarget)
        prefix = abspath(Environment.getSoftware())

        # If we specified the commands to run to obtain the target,
        # that's the only thing we will do.
        if commands:
            for cmd, tgt in commands:
                t.addCommand(cmd, targets=tgt, final=True)
                # Note that we don't use cwd=t.buildDir, so paths are
                # relative to SCIPION_HOME.
            return t

        # If we didn't specify the commands, we can either compile
        # with autotools (so we have to run "configure") or cmake.

        environ = os.environ.copy()
        for envVar, value in [('CPPFLAGS', '-I%s/include' % prefix),
                              ('LDFLAGS', '-L%s/lib' % prefix)]:
            environ[envVar] = '%s %s' % (value, os.environ.get(envVar, ''))

        if not cmake:
            flags.append('--prefix=%s' % prefix)
            flags.append('--libdir=%s/lib' % prefix)
            t.addCommand('./configure %s' % ' '.join(flags),
                         targets=makeFile, cwd=configPath,
                         out=self.getLogFolder('%s_configure.log' % name),
                         always=configAlways, environ=environ)
        else:
            assert progInPath('cmake') or 'cmake' in sys.argv[2:], \
                "Cannot run 'cmake'. Please install it in your system first."

            flags.append('-DCMAKE_INSTALL_PREFIX:PATH=%s .' % prefix)
            t.addCommand('cmake %s' % ' '.join(flags),
                         targets=makeFile, cwd=configPath,
                         out=self.getLogFolder('%s_cmake.log' % name),
                         environ=environ)

        t.addCommand('make -j %d' % self._processors,
                     cwd=t.buildPath,
                     out=self.getLogFolder('%s_make.log' % name))

        t.addCommand('make install',
                     targets=targets,
                     cwd=t.buildPath,
                     out=self.getLogFolder('%s_make_install.log' % name),
                     final=True)

        if clean:
            t.addCommand('make clean',
                         cwd=t.buildPath,
                         out=self.getLogFolder('%s_make_clean.log' % name))
            t.addCommand('rm %s' % makeFile)

        return t

    def addPipModule(self, name, version="", pipCmd=None,
                     target=None, default=True, deps=[]):
        """Add a new module to our built Python. Params in kwargs:

            :param name: pip module name
            :param version: module version - must be specified to prevent undesired updates.
            :param default: Optional. True if the module has to be installed right after the installation/update of the plugin.

            :returns target containing the pip module definition
        """

        target = name if target is None else target
        pipCmd = pipCmd or self._pipCmd % (name, version)
        t = self.addTarget(name, default=default, always=True)  # we set always=True to let pip decide if updating

        # Add the dependencies
        defaultDeps = []

        self._addTargetDeps(t, defaultDeps + deps)

        t.addCommand(pipCmd,
                     final=True,
                     targets="%s/%s" % (self.getPythonPackagesFolder(), target),
                     always=True  # execute pip command always. Pip will handle target existence
                     )

        return t

    def addPackage(self, name, **kwargs):
        """ Download a package tgz, untar it and create a link in software/em. Params in kwargs:


            :param tar: the package tar file, by default the name + .tgz. Pass None or VOID_TGZ if there is no tar file.
            :param commands: a list with actions to be executed to install the package
            :param buildDir: Optional folder where build/extraction happens. If not passed will be inferred from tgz's name
            :param neededProgs: Optional, list of programs needed. E.g: make, cmake,...
            :param version: Optional, version of the package.
            :param libChecks: Optional, a list of the libraries needed. E.g: libjpeg62, gsl (GSL - GNU Scientific Library)

        """
        # Add to the list of available packages, for reference (used in --help).
        neededProgs = kwargs.get('neededProgs', [])

        if name in sys.argv[2:]:
            # Check that we have the necessary programs in place.
            for prog in neededProgs:
                assert progInPath(prog), ("Cannot find necessary program: %s\n"
                                          "Please install and try again" % prog)

        if name not in self._packages:
            self._packages[name] = []

        # Get the version from the kwargs
        if 'version' in kwargs:
            version = kwargs['version']
            extName = self._getExtName(name, version)
        else:
            version = ''
            extName = name

        # Check the required libraries
        commands = kwargs.get('commands', [])
        if 'libChecks' in kwargs:
            cmdLibChecks = []
            libChecks = kwargs['libChecks']
            libChecks = list(libChecks) if type(libChecks) == str else libChecks
            for libName in libChecks:
                if not checkLib(libName):
                    msg = 'ERROR! Required library %s was not found. Please consider to install it ' \
                          '(sudo apt-get install in Ubuntu, sudo yum install in centOS, etc).' % libName
                    cmdLibChecks.append(('echo "%s" && exit 1' % redStr(msg), libName))

            if cmdLibChecks:
                commands = cmdLibChecks

        self._packages[name].append((name, version))

        environ = (self.updateCudaEnviron(name)
                   if kwargs.get('updateCuda', False) else None)

        # Set environment
        variables = kwargs.get('vars', {})
        if variables:
            environ = {} if environ is None else environ
            environ.update(variables)

        # We reuse the download and untar from the addLibrary method
        # and pass the createLink as a new command 
        tar = kwargs.get('tar', '%s.tgz' % extName)

        # If tar is None or void.tgz
        if tar is None or tar == VOID_TGZ:
            tar = VOID_TGZ
            kwargs["buildDir"] = extName
            kwargs["createBuildDir"] = True

        buildDir = self._getBuildDir(kwargs, tar)
        targetDir = kwargs.get('targetDir', buildDir)

        libArgs = {'downloadDir': self.getEmFolder(),
                   'urlSuffix': 'em',
                   'default': False,
                   'buildDir': buildDir}  # This will be updated with value in kwargs
        libArgs.update(kwargs)

        target = self._addDownloadUntar(extName, **libArgs)
        for cmd, tgt in commands:
            if isinstance(tgt, str):
                tgt = [tgt]

            # Take all package targets relative to package build dir
            normTgt = []
            for t in tgt:
                # Check for empty targets and warn about them
                if not t:
                    print("WARNING: Target empty for command %s" % cmd)

                normTgt.append(join(target.targetPath, t))

            target.addCommand(cmd, targets=normTgt, cwd=target.buildPath,
                              final=True, environ=environ)

        target.addCommand(Command(self, Link(extName, targetDir),
                                  targets=[self.getEm(extName),
                                           self.getEm(targetDir)],
                                  cwd=self.getEm('')),
                          final=True)

        # Create an alias with the name for that version
        # this implies that the last package version added will be
        # the one installed by default, so the last versions should
        # be the last ones to be inserted
        self.addTargetAlias(extName, name)

        return target

    def _getBuildDir(self, kwargs, tarFile):

        return kwargs.get('buildDir',
                   tarFile.rsplit('.tar.gz', 1)[0].rsplit('.tgz', 1)[0].rsplit('.tar')[0])

    def _showTargetGraph(self, targetList):
        """ Traverse the targets taking into account
        their dependencies and print them in DOT format.
        """
        print('digraph libraries {')
        for tgt in targetList:
            deps = tgt.getDeps()
            if deps:
                print('\n'.join("  %s -> %s" % (tgt, x) for x in deps))
            else:
                print("  %s" % tgt)
        print('}')

    def _showTargetTree(self, targetList, maxLevel=-1):
        """ Print the tree of dependencies for the given targets,
        up to a depth level of maxLevel (-1 for unlimited).
        """
        # List of (indent level, target)
        nodes = [(0, tgt) for tgt in targetList[::-1]]
        while nodes:
            lvl, tgt = nodes.pop()
            print("%s- %s" % ("  " * lvl, tgt))
            if maxLevel != -1 and lvl >= maxLevel:
                continue
            nodes.extend((lvl + 1, self._targetDict[x]) for x in tgt.getDeps())

    def _executeTargets(self, targetList):
        """ Execute the targets in targetList, running all their
        dependencies first.
        """
        executed = set()  # targets already executed
        exploring = set()  # targets whose dependencies we are exploring
        targets = targetList[::-1]
        while targets:
            tgt = targets.pop()
            if tgt.getName() in executed:
                continue
            deps = tgt.getDeps()
            if set(deps) - executed:  # there are dependencies not yet executed
                if tgt.getName() in exploring:
                    raise RuntimeError("Cyclic dependency on %s" % tgt)
                exploring.add(tgt.getName())
                targets.append(tgt)
                targets.extend(self._targetDict[x] for x in deps)
            else:
                tgt.execute()
                executed.add(tgt.getName())
                exploring.discard(tgt.getName())

    @staticmethod
    def _getExtName(name, version):
        """ Return folder name for a given package-version """
        return '%s-%s' % (name, version)

    def _isInstalled(self, name, version):
        """ Return true if the package-version seems to be installed. """
        pydir = self.getPythonPackagesFolder()
        extName = self._getExtName(name, version)
        return (exists(join(self.getEmFolder(), extName)) or
                extName in [x[:len(extName)] for x in os.listdir(pydir)])

    def printHelp(self):
        printStr = ""
        if self._packages:
            printStr = ("Available binaries: "
                        "([ ] not installed, [X] seems already installed)\n\n")

            keys = sorted(self._packages.keys())
            for k in keys:
                pVersions = self._packages[k]
                printStr += "{0:25}".format(k)
                for name, version in pVersions:
                    installed = self._isInstalled(name, version)
                    printStr += '{0:8}[{1}]{2:5}'.format(version, 'X' if installed else ' ', ' ')
                printStr += '\n'
        return printStr

    def execute(self):
        if '--help' in self._args:
            print(self.printHelp())
            return

        # Check if there are explicit targets and only install
        # the selected ones, ignore starting with 'xmipp'
        cmdTargets = [a for a in self._args
                      if a[0].isalpha()]
        if cmdTargets:
            # Check that they are all command targets
            for t in cmdTargets:
                if t not in self._targetDict:
                    raise RuntimeError("Unknown target: %s" % t)
            # Grab the targets passed in the command line
            targetList = [self._targetDict[t] for t in cmdTargets]
        else:
            # use all targets marked as default
            targetList = [t for t in self._targetList if t.isDefault()]

        if '--show-tree' in self._args:
            if '--dot' in self._args:
                self._showTargetGraph(targetList)
            else:
                self._showTargetTree(targetList)
        else:
            self._executeTargets(targetList)

    def updateCudaEnviron(self, package):
        """ Update the environment adding CUDA_LIB and/or CUDA_BIN to support
        packages that uses CUDA.
        package: package that needs CUDA to compile.
        """
        packUpper = package.upper()
        cudaLib = os.environ.get(packUpper + '_CUDA_LIB')
        cudaBin = os.environ.get(packUpper + '_CUDA_BIN')

        if cudaLib is None:
            cudaLib = pwem.Config.CUDA_LIB
            cudaBin = pwem.Config.CUDA_BIN

        environ = os.environ.copy()

        if os.path.exists(cudaLib):
            environ.update({'LD_LIBRARY_PATH': cudaLib + ":" +
                                               environ.get('LD_LIBRARY_PATH',"")})
        if cudaBin and os.path.exists(cudaBin):
            environ.update({'PATH': cudaBin + ":" + environ['PATH']})

        return environ

    def setDefault(self, default):
        """Set default values of all packages to the passed parameter"""
        for t in self._targetList:
            t.setDefault(default)

    def getPackages(self):
        """Return all plugin packages"""
        return self._packages

    def hasPackage(self, name):
        """ Returns true if it has the package"""
        return name in self._packages

    def getPackage(self, name):
        return self._packages.get(name, None)


class Link:
    def __init__(self, packageLink, packageFolder):
        self._packageLink = packageLink
        self._packageFolder = packageFolder

    def __call__(self):
        self.createPackageLink(self._packageLink, self._packageFolder)

    def __str__(self):
        return "Link '%s -> %s'" % (self._packageLink, self._packageFolder)

    def createPackageLink(self, packageLink, packageFolder):
        """ Create a link to packageFolder in packageLink, validate
        that packageFolder exists and if packageLink exists it is 
        a link.
        This function is supposed to be executed in software/em folder.
        """
        linkText = "'%s -> %s'" % (packageLink, packageFolder)

        if not exists(packageFolder):
            print(red("Creating link %s, but '%s' does not exist!!!\n"
                      "INSTALLATION FAILED!!!" % (linkText, packageFolder)))
            sys.exit(1)

        if exists(packageLink):
            if islink(packageLink):
                os.remove(packageLink)
            else:
                print(red("Creating link %s, but '%s' exists and is not a link!!!\n"
                          "INSTALLATION FAILED!!!" % (linkText, packageLink)))
                sys.exit(1)

        os.symlink(packageFolder, packageLink)
        print("Created link: %s" % linkText)


class CommandDef:
    """ Basic command class to hold the command string and the targets"""
    def __init__(self, cmd:str, targets:list=[]):
        """ Constructor

        e.g.: Command("git clone .../myrepo", "myrepo")

        :param cmd: String with the command/s to run.
        :param targets: Optional, a list or a string with file/s or folder/s that should exist as
         a consequence of the commands.

        """
        self._cmds = []
        self.new(cmd, targets)

    def new(self, cmd='', targets=None):
        """ Creates a new command element becoming the current command to do appends on it"""

        self._cmds.append([cmd, []])
        self.addTarget(targets)
        return self

    def isEmpty(self):
        return self._cmds[-1][0] == ''

    def addTarget(self, targets: list):
        """ Centralized internal method to add targets. They could be a list of string commands or a single command"""
        if targets is not None:
            lastTargets = self._cmds[-1][1]

            lastTargets.extend(targets if isinstance(targets, list) else [targets])
        return self

    def getCommands(self)->list:
        """ Returns the commands"""
        return self._cmds

    def append(self, newCmd:str, targets=None, sep="&&"):
        """ Appends an extra command to the existing one.

        :param newCmd: New command to append
        :param targets: Optional, additional targets in case this command produce them
        :param sep: Optional, separator used between the existing command and this new added one. (&&)

        :return itself Command
        """
        # Get the last command, target tuple
        lastCmdTarget = self._cmds[-1]

        cmd = lastCmdTarget[0]

        # If there is something already
        if cmd:
            cmd = "%s %s %s" % (cmd , sep, newCmd)
        else:
            cmd = newCmd

        lastCmdTarget[0] = cmd

        self.addTarget(targets)

        return self

    def cd(self, folder):
        """ Appends a cd command to the existing one

        :param folder: folder to changes director to
        """
        return self.append("cd %s" % folder)

    def touch(self, fileName, isTarget=True):
        """ Appends a touch command and its target based on the fileName

        :param fileName: file to touch. Should be created in the binary home folder. Use ../ in case of a previous cd command

        :return: CondaCommandDef (self)
        """
        if isTarget:
            # Add the touched file as target
            self.addTarget(fileName)

        return self.append("touch %s" % fileName, os.path.basename(fileName))


class CondaCommandDef(CommandDef):
    """ Extends CommandDef with some conda specific methods"""

    ENV_CREATED = "env-created.txt"

    def __init__(self, envName, condaActivationCmd=''):

        self._condaActivationCmd = condaActivationCmd.replace("&&", "")
        super().__init__("", None)

        self._envName=envName

    def create(self, extraCmds='', yml=None):
        """ Creates a conda environment with extra commands if passed

        :param extraCmds: additional commands (string) after the conda create -n envName

        :return: CondaCommandDef (self)

        """
        self.append(self._condaActivationCmd)
        if yml is None:
            self.append("conda create -y -n %s %s" % (self._envName, extraCmds))
        else:
            self.append("conda env create -y -n %s -f %s %s" % (self._envName, yml, extraCmds))
        return self.touch("env_created.txt")

    def pipInstall(self, packages):
        """ Appends pip install to the existing command adding packages"""

        return self.append("python -m pip install %s" % packages)

    def condaInstall(self, packages):
        """ Appends conda install to the existing command adding packages"""
        if self.isEmpty():
            self.activate(appendCondaActivation=True)

        return self.append("conda install %s" % packages)

    def activate(self, appendCondaActivation=False):
        """ Activates the conda environment

        :param appendCondaActivation: Pass true to prepend the conda activation command"""
        if appendCondaActivation:
            self.append(self._condaActivationCmd)

        return self.append("conda activate %s" % self._envName)

def mkdir(path):
    """ Creates a folder if it does not exist"""
    if not exists(path):
        os.makedirs(path)
    return path

class InstallHelper():
    """
    ### This class is intended to be used to ease the plugin installation process.

    #### Usage:
    InstallHelper class needs to be instanciated before it can be used.
    After that, commands can be chained together to run them in the defined order.
    The last command always needs to be addPackage().

    #### Example:
    installer = InstallHelper() # Instanciating class\n
    installer.getCloneCommand('test-package', '/home/user/myCustomPath', 'github.com/myRepo') # Cloning GitHub repository\n
    installer.getCondaenvCommand('test-package') # Creating conda enviroment\n
    installer.addPackage(env, 'test-package') # Install package\n

    #### It can also be done in a single line:
    installer.getCloneCommand('test-package', '/home/user/myCustomPath', 'github.com/myRepo').getCondaenvCommand('test-package').addPackage(env, 'test-package')\n

    #### If you want to check the command strings you are producing, use the function getCommandList() instead of addPackage() and assign it to a variable so you can print it.
    """
    # Global variables
    DEFAULT_VERSION = '1.0'

    def __init__(self, packageName: str, packageHome: str=None, packageVersion: str=DEFAULT_VERSION):
        """
        ### Constructor for the InstallHelper class.

        #### Parameters:
        packageName (str): Name of the package.
        packageHome (str): Optional. Path to the package. It can be absolute or relative to current directory.
        packageVersion (str): Optional. Package version.
        """
        # Temporary variables to store the count for autogenerated target files
        self.__genericCommands = 0
        self.__condaCommands = 0
        self.__extraFiles = 0

        # Private list of tuples containing commands with targets
        self.__commandList = []
        
        # Package name, version, and home
        self.__packageName = packageName
        self.__packageVersion = packageVersion
        self.__packageHome = packageHome if packageHome else os.path.join(pwem.Config.EM_ROOT, packageName + '-' + packageVersion)
    
    #--------------------------------------- PRIVATE FUNCTIONS ---------------------------------------#
    def __getTargetCommand(self, targetName: str) -> str:
        """
        ### This private function returns the neccessary command to create a target file given its name.
        ### Targets are always in uppercase and underscore format.

        #### Parameters:
        targetName (str): Name of the target file.

        #### Returns:
        (str): The command needed to create the target file.
        """
        return 'touch {}'.format(targetName)
    
    def __getBinaryEnvName(self, binaryName: str, binaryVersion: str=DEFAULT_VERSION) -> str:
        """
        ### This function returns the env name for a given package and repo.

        #### Parameters:
        binaryName (str): Name of the binary inside the package.
        binaryVersion (str): Optional. Binary's version.

        #### Returns:
        (str): The enviroment name for this binary.
        """
        return binaryName + "-" + binaryVersion
    
    def __getEnvActivationCommand(self, binaryName: str, binaryVersion: str=DEFAULT_VERSION) -> str:
        """
        ### Returns the conda activation command for the given enviroment.

        #### Parameters:
        binaryName (str): Name of the binary inside the package.
        binaryVersion (str): Optional. Version of the binary inside the package.

        #### Returns:
        (str): The enviroment activation command.
        """
        return "conda activate " + self.__getBinaryEnvName(binaryName, binaryVersion=binaryVersion)
    
    def __getBinaryNameAndVersion(self, binaryName: str=None, binaryVersion: str=None)  -> Tuple[str, str]:
        """
        ### Returns the binary name and version from an optionally introduced binary name and version.

        #### Parameters:
        binaryName (str): Name of the binary inside the package.
        binaryVersion (str): Optional. Version of the binary inside the package.

        #### Returns:
        tuple(str, str): The binary name and binary version.
        """
        binaryName = binaryName if binaryName else self.__packageName
        binaryVersion = binaryVersion if binaryVersion else self.__packageVersion
        return binaryName, binaryVersion
    
    #--------------------------------------- PUBLIC FUNCTIONS ---------------------------------------#
    def getCommandList(self) -> List[Tuple[str, str]]:
        """
        ### This function returns the list of commands with targets for debugging purposes or to export into another install helper.

        #### Returns:
        (list[tuple[str, str]]): Command list with target files.

        #### Usage:
        commandList = installer.getCommandList()
        """
        return self.__commandList
    
    def importCommandList(self, commandList: List[Tuple[str, str]]):
        """
        ### This function inserts the given formatted commands from another install helper into the current one.

        #### Parameters:
        commandList (list[tuple[str, str]]): List of commands generated by an install helper.

        #### Usage:
        installer1 = InstallHelper('package1', packageHome='/home/user/package2', packageVersion='1.0')
        installer1.addCommand('cd /home', 'CHANGED_DIRECTORY')
        installer2 = InstallHelper('package2', packageHome='/home/user/package2', packageVersion='1.0')
        installer2.importCommandList(installer1.getCommandList())

        #### Note:
        Argument 'packageHome' of the first installer must be the same as second installer.
        """
        # Adding given commands to current list
        self.__commandList.extend(commandList)
        return self
    
    def addCommand(self, command: str, targetName: str='', workDir: str=''):
        """
        ### This function adds the given command with target to the command list.
        ### The target file needs to be located inside packageHome's directory so Scipion can detect it.

        #### Parameters:
        command (str): Command to be added.
        targetName (str): Optional. Name of the target file to be produced after commands are completed successfully.
        workDir (str): Optional. Directory where the command will be executed from.

        #### Usage:
        installer.addCommand('python3 myScript.py', targetName='MYSCRIPT_COMPLETED', workDir='/home/user/Documents/otherDirectory')

        #### This function call will generate the following commands:
        cd /home/user/Documents/otherDirectory && python3 myScript.py && touch /home/user/scipion/software/em/test-package-1.0/MYSCRIPT_COMPLETED
        """
        # Getting work directory
        workDirCmd = 'cd {} && '.format(workDir) if workDir else ''

        # Getting target name
        if not targetName:
            targetName = f'COMMAND_{self.__genericCommands}'
            self.__genericCommands += 1
        fullTargetName = os.path.join(self.__packageHome, targetName)

        command = (workDirCmd + command) if workDir else command
        self.__commandList.append((command + " && {}".format(self.__getTargetCommand(fullTargetName)), targetName))
        return self
    
    def addCommands(self, commandList: List[str], binaryName: str=None, workDir:str='', targetNames: List[str]=[]):
        """
        ### This function adds the given commands with targets to the command list.

        #### Parameters:
        commandList (list[str]): List containing the commands to add.
        binaryName (str): Optional. Name of the binary. Default is package name.
        workDir (str): Optional. Directory where the commands will be executed from.
        targetNames (list[str]): Optional. List containing the name of the target files for this commands.

        #### Usage:
        installer.addCommands(['python3 myScript.py', 'ls'], binaryName='myBinary', workDir='/home/user/Documents/otherDirectory',
            targetNames=['MYSCRIPT_COMPLETED', 'DIRECTORY_LISTED'])

        #### This function call will generate the following commands:
        cd /home/user/Documents/otherDirectory && python3 myScript.py && touch /home/user/scipion/software/em/test-package-1.0/MYSCRIPT_COMPLETED\n
        cd /home/user/Documents/otherDirectory && ls && touch /home/user/scipion/software/em/test-package-1.0/DIRECTORY_LISTED
        """
        # Checking if introduced target name list and command list have same size
        if targetNames and len(commandList) != len(targetNames):
                raise RuntimeError("Error: Introduced target name list is of size {}, but command list is of size {}.".format(len(targetNames), len(commandList)))

        # Defining binary name
        binaryName = self.__getBinaryNameAndVersion(binaryName=binaryName)[0]

        # Executing commands
        for idx in range(len(commandList)):
            targetName = targetNames[idx] if targetNames else ''
            self.addCommand(commandList[idx], targetName=targetName, workDir=workDir)

        return self
    
    def getCloneCommand(self, url: str, binaryFolderName: str='', targeName: str=None):
        """
        ### This function creates the neccessary command to clone a repository from Github.

        #### Parameters:
        url (str): URL to the git repository.
        binaryFolderName (str): Optional. Name of the binary directory.
        targetName (str): Optional. Name of the target file for this command.

        #### Usage:
        installer.getCloneCommand('https://github.com/myRepo.git', binaryFolderName='myCustomBinary', targeName='BINARY_CLONED')

        #### This function call will generate the following command:
        cd /home/user/scipion/software/em/test-package-1.0 && git clone https://github.com/myRepo.git myCustomBinary && touch BINARY_CLONED
        """
        # Defining target name
        targeName = targeName if targeName else '{}_CLONED'.format(binaryFolderName.upper())

        # Modifying binary name with a space for the command
        binaryFolderName = (' ' + binaryFolderName) if binaryFolderName else ''

        # Adding command
        self.addCommand('git clone {}{}'.format(url, binaryFolderName), targeName, workDir=self.__packageHome)

        return self
    
    def getCondaEnvCommand(self, binaryName: str=None, binaryPath: str=None, binaryVersion: str=None, pythonVersion: str=None, requirementsFile: bool=False,
                           requirementFileName: str='requirements.txt', requirementList: List[str]=[], extraCommands: List[str]=[], targetName: str=None):
        """
        ### This function creates the command string for creating a Conda enviroment and installing required dependencies for a given binary inside a package.

        #### Parameters:
        binaryName (str): Optional. Name of the binary. Default is package name.
        binaryPath (str): Optional. Path to the binary. It can be absolute or relative to current directory.
        binaryVersion (str): Optional. Binary's version. Default is package version.
        pythonVersion (str): Optional. Python version needed for the package.
        requirementsFile (bool): Optional. Defines if a Python requirements file exists.
        requirementFileName (bool): Optional. Name of the Python requirements file.
        requirementList (list[str]): Optional. List of Python packages to be installed. Can be used together with requirements file, but packages cannot be repeated.
        extraCommands (list[str]): Optional. List of extra conda-related commands to execute within the conda enviroment.
        targetName (str): Optional. Name of the target file for this command.

        #### Usage:
        installer.getCondaEnvCommand(binaryName='myBinary', binaryPath='/home/user/scipion/software/em/test-package-1.0/myBinary', binaryVersion='1.5', pythonVersion='3.11',
            requirementsFile=True, requirementFileName='requirements.txt', requirementList=['torch==1.2.0', 'numpy'],
            extraCommands=['conda info --envs'], targetName='CONDA_ENV_CREATED')

        #### This function call will generate the following command:
        eval "$(/home/user/miniconda/bin/conda shell.bash hook)"&& conda create -y -n myBinary-1.5 python=3.11 && conda activate myBinary-1.5 &&
        cd /home/user/scipion/software/em/test-package-1.0/myBinary && conda install pip -y && $CONDA_PREFIX/bin/pip install -r requirements.txt &&
        $CONDA_PREFIX/bin/pip install torch==1.2.0 numpyconda info --envs && cd /home/user/scipion/software/em/test-package-1.0 && touch CONDA_ENV_CREATED
        #### The path in the first command (eval ...) might vary, depending on the value of CONDA_ACTIVATION_CMD in your scipion.conf file.
        """
        # Binary name and version definition
        binaryName, binaryVersion = self.__getBinaryNameAndVersion(binaryName=binaryName, binaryVersion=binaryVersion)

        # Conda env creation
        createEnvCmd = 'conda create -y -n {}{}'.format(self.__getBinaryEnvName(binaryName, binaryVersion=binaryVersion), (' python={}'.format(pythonVersion)) if pythonVersion else '')

        # Command to install pip
        pipInstallCmd = 'conda install pip -y'

        # Command prefix for Python packages installation
        requirementPrefixCmd = '$CONDA_PREFIX/bin/pip install'

        # Requirements file name
        requirementFileName = os.path.join(binaryPath, requirementFileName) if requirementFileName and binaryPath else requirementFileName

        # Command for installing Python packages with requirements file
        installWithFile = (requirementPrefixCmd + ' -r ' + requirementFileName) if requirementsFile else ''

        # Command for installing Python packages manually
        installManual = ' '.join(requirementList)
        installManual = (requirementPrefixCmd + " " + installManual) if installManual else ''

        # Only install pip and Python packages if requiremenst file or manual list has been provided
        pythonCommands = ''
        if installWithFile or installManual:
            pythonCommands = ' && ' + pipInstallCmd
            pythonCommands += ' && {}'.format(installWithFile) if installWithFile else ''
            pythonCommands += ' && {}'.format(installManual) if installManual else ''
        
        # Defining target name
        targetName = targetName if targetName else '{}_CONDA_ENV_CREATED'.format(binaryName.upper())
        
        # Crafting final command string
        command = pwem.Plugin.getCondaActivationCmd() + ' ' + createEnvCmd                          # Basic commands: hook and env creation
        command += ' && ' + self.__getEnvActivationCommand(binaryName, binaryVersion=binaryVersion) # Env activation
        if binaryPath:
            command += ' && cd {}'.format(binaryPath)                                               # cd to binary path if proceeds
        command += pythonCommands                                                                   # Python related commands
        if extraCommands:
            command += " && " + " && ".join(extraCommands)                                          # Extra conda commands
        if binaryPath:
            command += ' && cd {}'.format(self.__packageHome)                                       # Return to package's root directory
        
        # Adding command
        self.addCommand(command, targetName)
        return self
    
    def addCondaPackages(self, packages: List[str], binaryName: str=None, binaryVersion: str=None, channel: str=None, targetName: str=None):
        """
        ### This function returns the command used for installing extra packages in a conda enviroment.

        #### Parameters:
        binaryName (str): Name of the binary. Default is package name.
        packages (list[str]): List of conda packages to install.
        binaryVersion (str): Optional. Binary's version. Default is package version.
        channel (str): Optional. Channel to download the package from.
        targetName (str): Optional. Name of the target file for this command.

        #### Usage:
        installer.addCondaPackages(packages=['pytorch==1.1.0', 'cudatoolkit=10.0'], binaryName='myBinary',
            binaryVersion='1.5', channel='conda-forge', targetName='CONDA_PACKAGES_INSTALLED')

        #### This function call will generate the following command:
        eval "$(/home/user/miniconda/bin/conda shell.bash hook)"&& conda activate myBinary-1.5 &&
        conda install -y pytorch==1.1.0 cudatoolkit=10.0 -c conda-forge && touch CONDA_PACKAGES_INSTALLED
        #### The path in the first command (eval ...) might vary, depending on the value of CONDA_ACTIVATION_CMD in your scipion.conf file.
        """
        # Binary name and version definition
        binaryName, binaryVersion = self.__getBinaryNameAndVersion(binaryName=binaryName, binaryVersion=binaryVersion)

        # Defininig target name
        if not targetName:
            targetName = 'CONDA_COMMAND_{}'.format(self.__condaCommands)
            self.__condaCommands += 1

        # Adding installation command
        command = "{} {} && conda install -y {}".format(pwem.Plugin.getCondaActivationCmd(), self.__getEnvActivationCommand(binaryName, binaryVersion=binaryVersion), ' '.join(packages))
        if channel:
            command += " -c {}".format(channel)
        self.addCommand(command, targetName)

        return self
    
    def getExtraFile(self, url: str, targetName: str='', location: str=".", workDir: str='', fileName: str=None):
        """
        ### This function creates the command to download with wget the file in the given link into the given path.
        ### The downloaded file will overwrite a local one if they have the same name.
        ### This is done to overwrite potential corrupt files whose download was not fully completed.

        #### Parameters:
        url (str): URL of the resource to download.
        targetName (str): Optional. Name of the target file for this command.
        location (str): Optional. Location where the file will be downloaded. It can be absolute or relative to current directory.
        workDir (str): Optional. Directory where the file will be downloaded from.
        fileName (str): Optional. Name of the file after the download. Use intended for cases when expected name differs from url name.

        #### Usage:
        installer.getExtraFile('https://site.com/myfile.tar', targetName='FILE_DOWNLOADED', location='/home/user/scipion/software/em/test-package-1.0/subdirectory', workDir='/home/user', fileName='test.tar')

        #### This function call will generate the following command:
        cd /home/user && mkdir -p /home/user/scipion/software/em/test-package-1.0/subdirectory &&
        wget -O /home/user/scipion/software/em/test-package-1.0/subdirectory/test.tar https://site.com/myfile.tar && touch /home/user/scipion/software/em/test-package-1.0/FILE_DOWNLOADED
        """
        # Getting filename for wget
        fileName = fileName if fileName else os.path.basename(url)
        mkdirCmd = "mkdir -p {} && ".format(location) if location else ''

        # Defining target file name
        if not targetName:
            targetName = 'EXTRA_FILE_{}'.format(self.__extraFiles)
            self.__extraFiles += 1

        downloadCmd = "{}wget -O {} {}".format(mkdirCmd, os.path.join(location, fileName), url)
        self.addCommand(downloadCmd, targetName=targetName, workDir=workDir)

        return self

    def getExtraFiles(self, fileList: List[Dict[str, str]], binaryName: str=None, workDir: str='', targetNames: List[str]=None):
        """
        ### This function creates the command to download with wget the file in the given link into the given path.
        ### The downloaded file will overwrite a local one if they have the same name.
        ### This is done to overwrite potential corrupt files whose download was not fully completed.

        #### Parameters:
        fileList (list[dict[str, str, str]]): List containing files to be downloaded. Example: [{'url': url1, 'path': path1, 'name': 'test.tar'}, {'url': url2, 'path': path2, 'name': 'test2.tar'}]
        binaryName (str): Optional. Name of the binary.
        Each file is a list contaning url and location to download it. Paths can be an empty string for default location.
        workDir (str): Optional. Directory where the files will be downloaded from.
        targetNames (list[str]): Optional. List containing the name of the target files for this commands.

        #### Usage:
        installer.getExtraFiles(
            [
                {'url': 'https://site.com/myfile.tar', 'path': '/home/user/scipion/software/em/test-package-1.0/subdirectory1', 'name': 'test.tar'},
                {'url': 'https://site.com/myfile.tar2', 'path': '/home/user/scipion/software/em/test-package-1.0/subdirectory2', 'name': 'test2.tar2'}
            ],
            binaryName='myBinary', workDir='/home/user', targetNames=['DOWNLOADED_FILE_1', 'DOWNLOADED_FILE_2'])

        #### This function call will generate the following commands:
        cd /home/user && mkdir -p /home/user/scipion/software/em/test-package-1.0/subdirectory1 &&
        wget -O /home/user/scipion/software/em/test-package-1.0/subdirectory1/test.tar https://site.com/myfile.tar && touch /home/user/scipion/software/em/test-package-1.0/DOWNLOADED_FILE_1
        
        cd /home/user && mkdir -p /home/user/scipion/software/em/test-package-1.0/subdirectory2 &&
        wget -O /home/user/scipion/software/em/test-package-1.0/subdirectory2/test2.tar2 https://site.com/myfile.tar2 && touch /home/user/scipion/software/em/test-package-1.0/DOWNLOADED_FILE_2
        """
        # Checking if introduced target name list and file list have same size
        if targetNames and len(fileList) != len(targetNames):
            raise RuntimeError("Error: Introduced target name list is of size {}, but file list is of size {}.".format(len(targetNames), len(fileList)))
        
        # Defining binary name
        binaryName = self.__getBinaryNameAndVersion(binaryName=binaryName)[0]

        # For each file in the list, download file
        for idx in range(len(fileList)):
            # Checking if file dictionary contains url
            if 'url' not in fileList[idx]:
                raise KeyError("ERROR: Download url has not been set for at least one file. You can create the appropiate dictionary calling function getFileDict.")
            
            # Getting proper file dictionary
            kwargs = {}
            if 'name' in fileList[idx]:
                kwargs['name'] = fileList[idx]['name']
            if 'path' in fileList[idx]:
                kwargs['path'] = fileList[idx]['path']
            downloadable = fileList[idx] if ('path' in fileList[idx] and 'name' in fileList[idx]) else self.getFileDict(fileList[idx]['url'], **kwargs)

            targetName = targetNames[idx] if targetNames else ''
            self.getExtraFile(downloadable['url'], targetName=targetName, location=downloadable['path'], workDir=workDir, fileName=downloadable['name'])

        return self
    
    def addPackage(self, env, dependencies: List[str]=[], default: bool=True, **kwargs):
        """
        ### This function adds the given package to scipion installation with some provided parameters.
        
        #### Parameters:
        env: Scipion enviroment.
        dependencies (list[str]): Optional. List of dependencies the package has.
        default (bool): Optional. Defines if this package version is automatically installed with the plugin.
        **kwargs: Optional. Other possible keyword parameters that will be directly passed to env.addPackage.
        Intended for cases where multiple versions of the same package coexist in the same plugin.

        #### Usage:
        installer.addPackage(env, dependencies=['wget', 'conda'], default=True)
        """
        env.addPackage(self.__packageName, version=self.__packageVersion, tar='void.tgz', commands=self.__commandList, neededProgs=dependencies, default=default, **kwargs)
    
    #--------------------------------------- PUBLIC UTILS FUNCTIONS ---------------------------------------#
    def getFileDict(self, url: str, path: str='.', fileName: str=None) -> Dict[str, str]:
        """
        ### This function generates the dictionary for a downloadable file.
        
        #### Parameters:
        url (str): Url of the file to download.
        path (str): Optional. Relative or absolute path to download the file to.
        fileName (str): Optional. Local file name intented for that file after the download.

        #### Returns:
        (dict[str, str]): Dictionary prepared for the download of one file for function getExtraFiles.

        #### Usage:
        getFileDict('https://www.mywebsite.com/downloads/file.tar.gz', path='/path/to/myfile', fileName='newFile.tar.gz')
        """
        # Getting file name
        fileName = fileName if fileName else os.path.basename(url)

        # Returning dictionary
        return {'url': url, 'path': path, 'name': fileName}
