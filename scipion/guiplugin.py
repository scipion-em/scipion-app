# NOTE: This is far from ideal.
# We want to register actions in pyworkflow windows.
# Since pyworkflow scans packages, this init will be triggered by pyworkflow and then
# we will register the menu (only works for the project window and not for the "project list" window.
# register plugin menus
import os

from scipion.scripts.kickoff import (getTemplates, chooseTemplate,
                                     resolveTemplate,
                                     importTemplate)
from scipion.utils import getInstallPath, getScriptsPath
from scipion.constants import PLUGIN_MANAGER_PY, PYTHON, KICKOFF


def launchPluginManager(window):
    os.system("%s %s" % (PYTHON, os.path.join(getInstallPath(), PLUGIN_MANAGER_PY)))


def launchTemplates(window):
    os.system("%s %s" % (PYTHON, os.path.join(getScriptsPath(), KICKOFF)))

# Cancel this for now to prevent an early import of Config and a false initialization
from pyworkflow.gui.project import ProjectManagerWindow, ProjectWindow

ProjectManagerWindow.registerPluginMenu("Plugin manager", launchPluginManager, None)
ProjectManagerWindow.registerPluginMenu("Workflow templates", launchTemplates, None)


def importFromTemplate(window):
    templates = getTemplates()
    chosenTemplate = chooseTemplate(templates, parentWindow=window.getRoot())
    if chosenTemplate is not None and resolveTemplate(chosenTemplate, [],
                                                      showScheduleOption=False,
                                                      schedule=False,
                                                      showProjectOption=False,
                                                      showProject=False,
                                                      showProjectName=False):
        importTemplate(chosenTemplate, window)


ProjectWindow.registerPluginMenu("Import workflow template", importFromTemplate,
                                 None)
