#
# Modes (first argument given to scipion).
#

MODE_MANAGER = 'manager'
MODE_PROJECT = 'project'
MODE_LAST = 'last'  # shortcut to 'project last'
MODE_HERE = 'here'  # shortcut to 'project here'
MODE_TESTS = 'tests'  # keep tests for compatibility
MODE_TEST = 'test'  # also allow 'test', in singular
MODE_TEST_DATA = 'testdata'
MODE_HELP = 'help'
MODE_VIEWER = ['viewer', 'view', 'show']

# Installation modes
MODE_PLUGINS = 'plugins'
MODE_INSTALL_PLUGIN = ['installp', "install"]
MODE_UNINSTALL_PLUGIN = ['uninstallp', 'uninstall']
MODE_INSTALL_BINS = 'installb'
MODE_UNINSTALL_BINS = 'uninstallb'
MODE_CONFIG = 'config'
MODE_VERSION = 'version'
MODE_RUNPROTOCOL = 'runprotocol'
MODE_PROTOCOLS = 'protocols'
MODE_ENV = 'printenv'
MODE_RUN = 'run'
MODE_PYTHON = 'python'
MODE_TEMPLATE = 'template'
MODE_INSPECT = "inspect"
MODE_UPDATE = 'update'
MODE_PIP = 'pip'
PLUGIN_MODES = [MODE_UNINSTALL_PLUGIN[0], MODE_UNINSTALL_PLUGIN[1],
                MODE_INSTALL_PLUGIN[1], MODE_INSTALL_PLUGIN[0],
                MODE_INSTALL_BINS,
                MODE_UNINSTALL_BINS]

# Entry points
SCIPION_EP = "scipion"

# python file name: at install or scripts
PLUGIN_MANAGER_PY = 'plugin_manager.py'
PYTHON = 'python'
KICKOFF = 'kickoff.py'
