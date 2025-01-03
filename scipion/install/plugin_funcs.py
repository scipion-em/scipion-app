import requests
import os
import re
import sys
import json
import pkg_resources
from pkg_resources import parse_version

from .funcs import Environment
from pwem import Domain
from pyworkflow.utils import redStr, yellowStr
from pyworkflow.utils.path import cleanPath
from pyworkflow import LAST_VERSION, CORE_VERSION, Config
from importlib import reload

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


class PluginInfo(object):

    def __init__(self, pipName="", name="", pluginSourceUrl="", remote=True,
                 plugin=None, **kwargs):
        self.pipName = pipName
        self.name = name
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
        self.dirName = ""
        self.pipVersion = ""
        self.binVersions = []
        self.pluginEnv = None

        # Distribution
        self._dist = None
        self._plugin = plugin
        if self.remote:
            self.setRemotePluginInfo()
        else:
            self.setFakedRemotePluginInfo()

        self.setLocalPluginInfo()  # get local info if installed

    # ###################### Install funcs ############################

    def install(self):
        """Installs both pip module and default binaries of
        the plugin"""
        self.installPipModule()
        self.installBin()
        self.setLocalPluginInfo()

    def _getDistribution(self):
        if self._dist is None:
            try:
                self._dist = pkg_resources.get_distribution(self.pipName)
            except:
                pass
        return self._dist

    def _getPlugin(self):
        if self._plugin is None:

            try:
                dirname = self.getDirName()
                self._plugin = Config.getDomain().getPluginModule(dirname)
            except:
                pass
        return self._plugin

    def hasPipPackage(self):
        """Checks if the current plugin is installed via pip"""
        return self._getDistribution() is not None

    def isInstalled(self):
        """Checks if the current plugin is installed (i.e. has pip package).
        NOTE: we might want to change definition of isInstalled, hence the extra function."""
        reload(pkg_resources)
        return self.hasPipPackage()

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
                if os.path.exists(os.path.join(self.pluginSourceUrl, 'pyproject.toml')):
                    target = target.replace('-', '_')
            else:
                # path doesn't exist, we assume is git and force install
                installSrc = '--upgrade git+%s' % self.pluginSourceUrl
                target = "%s*" % self.pipName.replace('-', '_')
        else:
            # install from pypi
            installSrc = "%s==%s" % (self.pipName, version)
            target = "%s*" % self.pipName.replace('-', '_')

        cmd = PIP_CMD % {'installSrc': installSrc}

        environment.addPipModule(self.pipName,
                                             target=target,
                                             pipCmd=cmd)

        # check if we're doing a version change of an already installed plugin
        reloadPkgRes = self.isInstalled()

        environment.execute()
        # we already have a dir for the plugin:
        if reloadPkgRes:
            # if plugin was already installed, pkg_resources has the old one
            # so it needs a reload
            reload(pkg_resources)
            self.dirName = self.getDirName()
            Domain.refreshPlugin(self.dirName)
            self._plugin = None
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
        args = (PIP_UNINSTALL_CMD % self.pipName).split()
        subprocess.call(PIP_UNINSTALL_CMD % self.pipName, shell=True,
                        stdout=sys.stdout,
                        stderr=sys.stderr)

    # ###################### Remote data funcs ############################

    def getPipJsonData(self):
        """"Request json data from pypi, return json content"""
        pipData = requests.get("%s/%s/json" % (PIP_BASE_URL, self.pipName))
        if pipData.ok:
            pipData = pipData.json()
            return pipData
        else:
            print("Warning: Couldn't get remote plugin data for %s" % self.pipName)
            return {}

    def getCompatiblePipReleases(self, pipJsonData=None):
        """Get pip releases of this plugin that are compatible with
         current Scipion version. Returns dict with all compatible releases and
         a special key "latest" with the most recent one."""

        if pipJsonData is None:
            pipJsonData = self.getPipJsonData()

        reg = r'scipion-([\d.]*\d)'
        releases = {}
        latestCompRelease = NULL_VERSION

        for release, releaseData in pipJsonData['releases'].items():
            releaseData = releaseData[0]
            scipionVersions = [parse_version(v)
                               for v in re.findall(reg,
                                                   releaseData['comment_text'])]
            if len(scipionVersions) != 0:
                releases[release] = releaseData
                if any([v == parse_version(CORE_VERSION)
                        for v in scipionVersions]):
                    if parse_version(latestCompRelease) < parse_version(release):
                        latestCompRelease = release
            else:
                print(yellowStr("WARNING: %s's release %s did not specify a "
                                "compatible Scipion version. Please, remove this "
                                "release from pypi") % (self.pipName, release))

        releases['latest'] = latestCompRelease
        return releases

    def setRemotePluginInfo(self):
        """Sets value for the attributes that need to be obtained from pypi"""
        pipData = self.getPipJsonData()
        if not pipData:
            return
        info = pipData['info']
        releases = self.getCompatiblePipReleases(pipJsonData=pipData)

        self.homePage = self.getPipData(info, ['home_page', 'project_urls.Homepage'])
        self.summary = self.getPipData(info, ['summary'])
        self.author = self.getPipData(info, ['author', 'author_email'])
        self.email = self.getPipData(info, ['author_email'])
        self.compatibleReleases = releases
        self.latestRelease = releases['latest']

    def setFakedRemotePluginInfo(self):
        """Sets value for the attributes that need to be obtained from json file"""
        self.homePage = self.pluginSourceUrl
        self.compatibleReleases = {DEVEL_VERSION: {'upload_time': '   devel_mode'}}
        self.latestRelease = DEVEL_VERSION
        self.author = ' Developer mode'

    def getPipData(self, info, keys):
        """
        Extracts a value from a dictionary (info) based on the primary key.
        Supports nested keys using dot notation (e.g., "project_urls.Homepage").

        :param info: Dictionary containing data (e.g., pip info).
        :param keys: List of keys to extract the value (dot notation for nested keys).
        :return: The extracted value or '' if no keys match.
        """

        def getNestedValue(data, key):
            keysList = key.split(".")
            for k in keysList:
                if isinstance(data, dict) and k in data:
                    data = data[k]
                else:
                    return None
            return data

        # Try backup keys if the main key doesn't yield a value
        for key in keys:
            value = getNestedValue(info, key)
            if value:
                return value
        return ' '

    # ###################### Local data funcs ############################

    def setLocalPluginInfo(self):
        """Sets value for the attributes that can be obtained locally if the
        plugin is installed."""
        if self.isInstalled():

            metadata = {}
            # Take into account 2 cases here:
            # A.: plugin is a proper pipmodule and is installed as such
            # B.: Plugin is not yet a pipmodule but a local folder.
            try:
                package = pkg_resources.get_distribution(self.pipName)
                keys = ['Name', 'Version', 'Summary', 'Home-page', 'Author',
                        'Author-email']
                pattern = r'(.*): (.*)'

                for line in package._get_metadata(package.PKG_INFO):
                    match = re.match(pattern, line)
                    if match:
                        key = match.group(1)
                        if key in keys:
                            metadata[key] = match.group(2)
                            keys.remove(key)
                            if not len(keys):
                                break

                self.pipVersion = metadata.get('Version', "")
                self.dirName = self.getDirName()
                self.binVersions = self.getBinVersions()

            except:
                # Case B: code local but not yet a pipmodule.
                pass

            if not self.remote:
                # only do this if we don't already have it from remote
                self.homePage = metadata.get('Home-page', "")
                self.summary = metadata.get('Summary', "")
                self.author = metadata.get('Author', "")
                self.email = metadata.get('Author-email', "")

    def getPluginClass(self):
        """ Tries to find the Plugin object."""
        pluginModule = self._getPlugin()

        if pluginModule is not None:
            pluginClass = pluginModule._pluginInstance
        else:
            print("Warning: couldn't find Plugin for %s" % self.pipName)
            print("Dirname: %s" % self.getDirName())
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
                print("Couldn't get binaries definition of %s plugin: %s" % (self.name, e))
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
                    redStr("Error retrieving plugin %s binaries: " % self.name), e)
        binVersions = [target.getName() for target in env.getTargetList() if target.getName() not in defaultTargets]
        return binVersions

    def getDirName(self):
        """Get the name of the folder that contains the plugin code
           itself (e.g. to import the _plugin object.)"""
        # top level file is a file included in all pip packages that contains
        # the name of the package's top level directory
        try:
            return pkg_resources.get_distribution(self.pipName).get_metadata('top_level.txt').strip()
        except Exception as e:
            return None

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
        return self.name

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
            pinfo = PluginInfo(name=p, plugin=pobj, remote=False)
            pbins = pinfo.getBinVersions()
            binToPluginDict.update({k: p for k in pbins})
            pbinsNoVersion = set([b.split('-', 1)[0] for b in pbins])
            binToPluginDict.update({k: p for k in pbinsNoVersion})
        return binToPluginDict

    def getPlugins(self, pluginList=None, getPipData=False):
        """Reads available plugins from self.repoUrl and returns a dict with
        PluginInfo objects. Params:
        - pluginList: A list with specific plugin pip-names we want to get.
        - getPipData: If true, each PluginInfo object will try to get the data
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
            pluginInfo = PluginInfo(**pluginsJson[pluginName])
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
        pluginDict = self.getPlugins(getPipData=withUpdates)
        if pluginDict:
            withBinsStr = "Installed plugins and their %s" % green("binaries") \
                if withBins else "Available plugins"
            printStr += ("%s: "
                         "([ ] not installed, [X] seems already installed)\n\n" % withBinsStr)
            keys = sorted(pluginDict.keys())
            for name in keys:
                plugin = pluginDict[name]
                if withBins and not plugin.isInstalled():
                    continue
                printStr += "{0:30} {1:10} [{2}]".format(name,
                                                         plugin.pipVersion,
                                                         'X' if plugin.isInstalled() else ' ')
                if withUpdates and plugin.isInstalled():
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

    return os.environ.get("SCIPION_DONT_INSTALL_BINARIES", True) == True