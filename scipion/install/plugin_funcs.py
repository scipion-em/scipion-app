import requests
import os
import sys
import json
from functools import lru_cache
from importlib import metadata
from packaging import version
import site
try:
    import importlib_metadata
except ModuleNotFoundError:
    raise ModuleNotFoundError('You are missing importlib-metadata package. '
                              'Please run: scipion3 pip install importlib-metadata')

from .funcs import Environment
from pwem import Domain
from pyworkflow.utils import redStr, yellowStr
from pyworkflow.utils.path import cleanPath
from pyworkflow import LAST_VERSION, CORE_VERSION, OLD_VERSIONS, Config


NULL_VERSION = "0.0.0"
# This constant is used in order to install all plugins taking into account a
# json file
DEVEL_VERSION = "999.9.9"

REPOSITORY_URL = Config.SCIPION_PLUGIN_JSON

if REPOSITORY_URL is None:
    REPOSITORY_URL = Config.SCIPION_PLUGIN_REPO_URL

PIP_BASE_URL = 'https://pypi.python.org/pypi'
PIP_CMD = '{0} -m pip install %(installSrc)s'.format(
    Environment.getPython())

PIP_UNINSTALL_CMD = '{0} -m pip uninstall -y %s'.format(
    Environment.getPython())

versions = list(OLD_VERSIONS) + [LAST_VERSION]


class PluginInfo(object):

    def __init__(self, pipName="", moduleName=None, pluginSourceUrl="", remote=False,
                 plugin=None, withBins=True, **kwargs):
        """ Main class responsible for plugin installation.
        :param pipName: pip/distribution name, e.g. scipion-em-relion
        :param moduleName: module name, e.g. relion
        :param pluginSourceUrl: url or local path
        :param remote: connect to PyPi if True
        :param plugin: Plugin object
        :param withBins: Query binary versions
        """
        self.pipName = pipName
        self.pluginSourceUrl = pluginSourceUrl
        self.remote = remote

        # things from pypi
        self.homePage = ""
        self.summary = ""
        self.author = ""
        self.email = ""
        self.compatibleReleases = {}
        self.latestRelease = ""

        # things we have when installed
        self.moduleName = moduleName
        self.pipVersion = ""
        self.binVersions = []
        self.pluginEnv = None

        # Distribution
        self._metadata = None
        self._plugin = plugin
        if self.remote:
            self.setRemotePluginInfo()
        else:
            self.setFakedRemotePluginInfo()

        self.setLocalPluginInfo(withBins=withBins)  # get local info if installed

    # ###################### Install funcs ############################

    def install(self):
        """Installs both pip module and default binaries of
        the plugin"""
        self.installPipModule()
        self.installBin()
        self.setLocalPluginInfo()

    def _getMetadata(self):
        if self._metadata is None:
            try:
                self._metadata = metadata.metadata(self.pipName)
            except metadata.PackageNotFoundError:
                pass
        return self._metadata

    def _getPlugin(self):
        if self._plugin is None:
            try:
                dirname = self.getModuleName()
                self._plugin = Config.getDomain().getPluginModule(dirname)
            except:
                pass
        return self._plugin

    def isInstalled(self):
        """Checks if the distribution metadata is available. """
        return self._getMetadata() is not None

    def installPipModule(self, version=""):
        """Installs the version specified of the pip plugin, as long as it is compatible
        with the current Scipion version. If no version specified, will install latest
        compatible one."""
        environment = Environment()

        if not version:
            version = self.latestRelease
        elif version not in self.compatibleReleases:
            if self.compatibleReleases:
                print('%s version %s not compatible with current Scipion '
                      'version %s.' % (self.pipName, version, LAST_VERSION))
                print("Please choose a compatible release: %s" % " ".join(
                    self.compatibleReleases.keys()))
            else:
                print("%s has no compatible versions with current Scipion "
                      "version %s." % (self.pipName, LAST_VERSION))
            return False

        if version == NULL_VERSION:
            print("Plugin %s is not available for this Scipion %s yet" % (self.pipName, LAST_VERSION))
            return False

        if self.pluginSourceUrl:
            if os.path.exists(self.pluginSourceUrl):
                # install from dir in editable mode
                installSrc = '-e %s' % self.pluginSourceUrl
                target = "%s*" % self.pipName
            else:
                # path doesn't exist, we assume is git and force install
                installSrc = '--upgrade git+%s' % self.pluginSourceUrl
                target = "%s*" % self.pipName.replace('-', '_')
        else:
            # install from pypi
            installSrc = "%s==%s" % (self.pipName, version)
            target = "%s*" % self.pipName.replace('-', '_')

        cmd = PIP_CMD % {'installSrc': installSrc}

        pipModule = environment.addPipModule(self.pipName,
                                             target=target,
                                             pipCmd=cmd)

        environment.execute()
        site.main()  # update module search path
        if self.isInstalled():
            Domain.refreshPlugin(self.getModuleName())
        return True

    def installBin(self, args=None):
        """Install binaries of the plugin. Args is the list of args to be
           passed to the install environment."""
        environment = self.getInstallenv(envArgs=args)
        environment.execute()

    def uninstallBins(self, binList=None):
        """Uninstall binaries of the plugin.

        :param binList: if  given, will uninstall the binaries in it. The binList
        may contain strings with only the name of the binary or
        name and version in the format name-version

        :returns None

        """
        if binList is None:
            binList = self.binVersions

        binFolder = Environment.getEmFolder()
        for binVersion in binList:
            f = os.path.join(binFolder, binVersion)
            if os.path.exists(f):
                print('Removing %s binaries...' % binVersion)
                realPath = os.path.realpath(f)  # in case it's a link
                cleanPath(f, realPath)
                print('Binary %s has been uninstalled successfully ' % binVersion)
            else:
                print('The binary %s does not exist ' % binVersion)
        return

    def uninstallPip(self):
        """Removes pip package from site-packages"""
        print('Removing %s plugin...' % self.pipName)
        import subprocess
        subprocess.call(PIP_UNINSTALL_CMD % self.pipName, shell=True,
                        stdout=sys.stdout,
                        stderr=sys.stderr)

    # ###################### Remote data funcs ############################

    @lru_cache()
    def getPipJsonData(self):
        """"Request json data from pypi, return json content"""
        with requests.get("%s/%s/json" % (PIP_BASE_URL, self.pipName)) as r:
            if r.status_code == 200:
                return r.json()
            else:
                print("Warning: Couldn't get remote plugin data for %s" % self.pipName)
                return {}

    def getCompatiblePipReleases(self, pipJsonData=None):
        """Get pip releases of this plugin that are compatible with
            current Scipion version. Returns dict with all compatible releases and
            a special key "latest" with the most recent one."""

        if pipJsonData is None:
            pipJsonData = self.getPipJsonData()

        releases = {}
        latestCompRelease = NULL_VERSION
        allReleases = pipJsonData['releases']
        supportedReleases = dict(filter(lambda item: "scipion-" in item[1][0]["comment_text"],
                                        allReleases.items()))
        unsupported = [v for v in allReleases.keys() if v not in supportedReleases.keys()]
        if unsupported:
            for i in unsupported:
                print(yellowStr("WARNING: %s release %s did not specify a "
                                "compatible Scipion version. Please remove this "
                                "release from pypi") % (self.pipName, i))

        def _compatible(item):
            """ Filter versions compatible with Scipion's core. """
            versionStr = item[1]["comment_text"].lstrip("scipion-")
            return version.Version(versionStr) == version.Version(CORE_VERSION)

        if supportedReleases:
            releases = {k: v[0] for k, v in supportedReleases.items()}
            compReleases = filter(_compatible, releases.items())
            compByVersions = sorted(compReleases, key=lambda x: version.Version(x[0]))
            if compByVersions:
                latestCompRelease = list(compByVersions)[-1][0]

        releases['latest'] = latestCompRelease

        return releases

    def setRemotePluginInfo(self):
        """Sets value for the attributes that need to be obtained from pypi"""
        pipData = self.getPipJsonData()
        if not pipData:
            return
        info = pipData['info']
        releases = self.getCompatiblePipReleases(pipJsonData=pipData)

        self.homePage = info['home_page']
        self.summary = info['summary']
        self.author = info['author']
        self.email = info['author_email']
        self.compatibleReleases = releases
        self.latestRelease = releases['latest']

    def setFakedRemotePluginInfo(self):
        """Sets value for the attributes that need to be obtained from json file"""
        self.homePage = self.pluginSourceUrl
        self.compatibleReleases = {DEVEL_VERSION: {'upload_time': '   devel_mode'}}
        self.latestRelease = DEVEL_VERSION
        self.author = ' Developer mode'

    # ###################### Local data funcs ############################

    def setLocalPluginInfo(self, withBins=True):
        """Sets value for the attributes that can be obtained locally if the
        plugin is installed."""
        if self.isInstalled():
            if withBins:
                self.binVersions = self.getBinVersions()

            self.pipVersion = self._metadata.get('Version', "")
            if not self.remote:
                # only do this if we don't already have it from remote
                self.homePage = self._metadata.get('Home-page', "")
                self.summary = self._metadata.get('Summary', "")
                self.author = self._metadata.get('Author', "")
                self.email = self._metadata.get('Author-email', "")

    def getPluginClass(self):
        """ Tries to find the Plugin object."""
        pluginModule = self._getPlugin()

        if pluginModule is not None:
            pluginClass = pluginModule._pluginInstance
        else:
            print("Warning: couldn't find Plugin for %s" % self.pipName)
            pluginClass = None
        return pluginClass

    def getInstallenv(self, envArgs=None):
        """Reads the defineBinaries function from Plugin class and returns an
        Environment object with the plugin's binaries."""
        if envArgs is None:
            envArgs = dict()

        env = Environment(**envArgs)
        env.setDefault(False)

        plugin = self.getPluginClass()
        if plugin is not None:
            try:
                plugin.defineBinaries(env)
            except Exception as e:
                print("Couldn't get binaries definition of %s plugin: %s" % (self.moduleName, e))
                import traceback
                traceback.print_exc()
            return env
        else:
            return None

    def getBinVersions(self):
        """Get list with names of binaries of this plugin"""
        env = Environment()
        env.setDefault(False)
        defaultTargets = [target.getName() for target in env.getTargetList()]
        plugin = self.getPluginClass()
        if plugin is not None:
            try:
                plugin.defineBinaries(env)
            except Exception as e:
                print(
                    redStr("Error retrieving plugin %s binaries: " % self.moduleName), e)
        binVersions = [target.getName() for target in env.getTargetList() if target.getName() not in defaultTargets]
        return binVersions

    def getModuleName(self):
        """ Get the top-level import package name that contains the plugin code.
            Ditributions names are not necessarily equivalent to or correspond 1:1 with the top-level import
            package names that can be imported inside Python code. One distribution package can
            contain multiple import packages (and single modules), and one top-level import package
            may map to multiple distribution packages if it is a namespace package.
            Example: scipion-em-relion (distribution) / relion (top-level module)
        """
        if self.moduleName is None:
            for module, distr in self.packages_distributions().items():
                if distr[0] == self.pipName:
                    self.moduleName = module
                    break

        return self.moduleName

    def packages_distributions(self):
        """ Return a mapping of top-level packages to their distributions.
        # TODO: deprecate this once we remove Python <3.10 support
        """
        try:
            return metadata.packages_distributions()
        except AttributeError:  # Python < 3.10
            return importlib_metadata.packages_distributions()

    def printBinInfoStr(self):
        """Returns string with info of binaries installed to print in console
        with flag --help"""
        try:
            env = self.getInstallenv()

            return env.printHelp().split('\n', 1)[1]
        except IndexError as noBins:
            return " ".rjust(14) + "No binaries information defined.\n"
        except Exception as e:
            return " ".rjust(14) + "Error getting binaries info: %s" % \
                   str(e) + "\n"

    def getPluginName(self):
        """Return the plugin name"""
        return self.moduleName

    def getPipName(self):
        """Return the plugin pip name"""
        return self.pipName

    def getPipVersion(self):
        """Return the plugin pip version"""
        return self.pipVersion

    def getSourceUrl(self):
        """Return the plugin source url"""
        return self.pluginSourceUrl

    def getHomePage(self):
        """Return the plugin Home page"""
        return self.homePage

    def getSummary(self):
        """Return the plugin summary"""
        return self.summary

    def getAuthor(self):
        """Return the plugin author"""
        return self.author

    def getReleaseDate(self, release):
        """Return the uploaded date from the release"""
        return self.compatibleReleases[release]['upload_time']

    def getLatestRelease(self):
        """Get the plugin latest release"""
        return self.latestRelease


class PluginRepository(object):

    def __init__(self, repoUrl=REPOSITORY_URL):
        self.repoUrl = repoUrl
        self.plugins = None

    @staticmethod
    def getBinToPluginDict():
        localPlugins = Domain.getPlugins()
        binToPluginDict = {}
        for p, pobj in localPlugins.items():
            pinfo = PluginInfo(moduleName=p, plugin=pobj)
            pbins = pinfo.getBinVersions()
            binToPluginDict.update({k: p for k in pbins})
            pbinsNoVersion = set([b.split('-', 1)[0] for b in pbins])
            binToPluginDict.update({k: p for k in pbinsNoVersion})
        return binToPluginDict

    def getPlugins(self, pluginList=None, getPipData=False, withBins=True):
        """Reads available plugins from self.repoUrl and returns a dict with
        PluginInfo objects. Params:
        - pluginList: A list with specific plugin pip-names we want to get.
        - getPipData: If true, each PluginInfo object will try to get the data
        - withBins: get binary versions
        of the plugin from pypi."""

        pluginsJson = {}
        if self.plugins is None:
            self.plugins = {}

        if os.path.isfile(self.repoUrl):
            with open(self.repoUrl) as f:
                pluginsJson = json.load(f)
            getPipData = False
        else:
            try:
                r = requests.get(self.repoUrl)
                getPipData = True
            except requests.ConnectionError as e:
                print("\nWARNING: Error while trying to connect with a server:\n"
                      "  > Please, check your internet connection!\n")
                print(e)
                return self.plugins
            if r.ok:
                pluginsJson = r.json()
            else:
                print("WARNING: Can't get Scipion's plugin list, the plugin "
                      "repository is not available")
                return self.plugins

        availablePlugins = pluginsJson.keys()

        if pluginList is None:
            targetPlugins = availablePlugins
        else:
            targetPlugins = set(availablePlugins).intersection(set(pluginList))
            if len(targetPlugins) < len(pluginList):
                wrongPluginNames = set(pluginList) - set(availablePlugins)
                print("WARNING - The following plugins didn't match available "
                      "plugin names:")
                print(" ".join(wrongPluginNames))
                print("You can see the list of available plugins with the following command:\n"
                      "scipion installp --help")

        for pluginName in targetPlugins:
            pluginsJson[pluginName].update(remote=getPipData)
            pluginInfo = PluginInfo(**pluginsJson[pluginName], withBins=withBins)
            if pluginInfo.getLatestRelease() != NULL_VERSION:
                self.plugins[pluginName] = pluginInfo

        return self.plugins

    def printPluginInfoStr(self, withBins=False, withUpdates=False):
        """Returns string to print in console which plugins are installed.

        :param withBins: If true, will add binary info for the plugins installed
        :param withUpdates: If true, will check if the installed plugins have new releases.

        :return A string with the plugin information summarized"""

        def ansi(n):
            """Return function that escapes text with ANSI color n."""
            return lambda txt: '\x1b[%dm%s\x1b[0m' % (n, txt)

        black, red, green, yellow, blue, magenta, cyan, white = map(ansi,
                                                                    range(30, 38))

        printStr = ""
        pluginDict = self.getPlugins(getPipData=withUpdates, withBins=withBins)
        if pluginDict:
            withBinsStr = "Installed plugins and their %s" % green("binaries") \
                if withBins else "Available plugins"
            printStr += ("%s: "
                         "([ ] not installed, [X] seems already installed)\n\n" % withBinsStr)
            keys = sorted(pluginDict.keys())
            for name in keys:
                plugin = pluginDict[name]
                isInstalled = plugin.isInstalled()
                if withBins and not isInstalled:
                    continue
                printStr += "{0:30} {1:10} [{2}]".format(name,
                                                         plugin.pipVersion,
                                                         'X' if isInstalled else ' ')
                if withUpdates and isInstalled:
                    if plugin.latestRelease != plugin.pipVersion:
                        printStr += yellow('\t(%s available)' % plugin.latestRelease)
                printStr += "\n"
                if withBins:
                    printStr += green(plugin.printBinInfoStr())
        else:
            printStr = "List of available plugins in plugin repository inaccessible at this time."

        return printStr


def installBinsDefault():
    """ Returns the default behaviour for installing binaries
    By default it is TRUE, define "SCIPION_DONT_INSTALL_BINARIES" to anything to deactivate binaries installation"""

    return os.environ.get("SCIPION_DONT_INSTALL_BINARIES", True)
