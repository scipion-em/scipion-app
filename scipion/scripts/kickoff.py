# -*- coding: utf-8 -*-
#!/usr/bin/env python
# **************************************************************************
# *
# * Authors:     Pablo Conesa (pconesa@cnb.csic.es)
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
"""
Creates a scipion workflow file (json formatted) base on a template.
The template may have some ~placeholders~ that will be overwritten with values
Template may look like this, separator is "~" and within it you can define:
~title|value|type~
Template string sits at the end of the file ready for a running streaming demo.
"""
import subprocess
import sys
import os
import re
import tkinter as tk
import tkinter.font as tkFont
import traceback
import time

import pyworkflow as pw
import pyworkflow.utils as pwutils
from pyworkflow.gui import Message, dialog
from pyworkflow.plugin import Template
from pyworkflow.project import ProjectSettings, Project
import pyworkflow.gui as pwgui
from pyworkflow.gui.project.base import ProjectBaseWindow
from pyworkflow.gui.widgets import HotButton, Button
from pyworkflow.template import TemplateList
from scipion.constants import SCIPION_EP, MODE_PROJECT

# Custom labels
from scipion.utils import getExternalJsonTemplates

ENTRY = 'entry'
LABEL = 'label'
CHECKBUTTON = 'Checkbutton'
YES = "Yes"
NO = "No"

FLAG_PARAM = "--"
NOGUI_FLAG = FLAG_PARAM + "nogui"
NOSCHEDULE_FLAG = FLAG_PARAM + "noschedule"


ACCEPT_BUTTON = "Accept"
LEN_LABEL_IN_CHARS = 30
LABEL_ALIGN_PATTERN = '{:>%s}' % LEN_LABEL_IN_CHARS
LEN_BUTTON_IN_CHARS = 12
BUTTON_ALIGN_PATTERN = "{:^%s}" % LEN_BUTTON_IN_CHARS

FIELD_SEP = '~'
VIEW_WIZARD = 'wizardview'

# Project name files
PROJECT_NAME = 'Project name'
DO_NOT_SCHEDULE = "Cancel schedule"
DO_NOT_SHOW_GUI = "Don't show the project"

# Project regex to validate the session id name
PROJECT_PATTERN = "^\w{2}\d{4,6}-\d+$"
PROJECT_REGEX = re.compile(PROJECT_PATTERN)


class KickoffWindow(ProjectBaseWindow):
    """ Windows to manage all projects. """

    def __init__(self, template, argsList, showScheduleOption, schedule,
                  showProjectOption, showProject, showProjectName):
        try:
            title = '%s (%s on %s)' % ('Workflow template customizer',
                                       pwutils.getLocalUserName(),
                                       pwutils.getLocalHostName())
        except Exception:
            title = Message.LABEL_PROJECTS

        settings = ProjectSettings()
        self.generalCfg = settings.getConfig()

        ProjectBaseWindow.__init__(self, title, minsize=(800, 350))
        self.template = template
        self.argsList = argsList
        self.showScheduleOption = showScheduleOption
        self.schedule = schedule
        self.showProjectOption = showProjectOption
        self.showProject = showProject
        self.showProjectName = showProjectName

        self.viewFuncs = {VIEW_WIZARD: KickoffView}
        self.action = Message.LABEL_BUTTON_CANCEL
        self.switchView(VIEW_WIZARD)

    def getTemplate(self):
        return self.template

    def getAction(self):
        return self.action

    def switchView(self, newView, **kwargs):
        # Destroy the previous view if exists:
        if self.viewWidget:
            self.viewWidget.grid_forget()
            self.viewWidget.destroy()
        # Create the new view: Instantiates KickoffView HERE!.
        self.viewWidget = self.viewFuncs[newView](self.footer, self,
                                                  template=self.template,
                                                  argsList=self.argsList,
                                                  showScheduleOption=self.showScheduleOption,
                                                  schedule=self.schedule,
                                                  showProjectOption=self.showProjectOption,
                                                  showProject=self.showProject,
                                                  showProjectName=self.showProjectName)

        # Grid in the second row (1)
        self.viewWidget.grid(row=0, column=0, columnspan=10, sticky='news')
        self.footer.rowconfigure(0, weight=1)
        self.footer.columnconfigure(0, weight=1)
        self.view = newView

    def _onClosing(self):
        self.root.destroy()
        if self.showScheduleOption and self.showProjectOption:
            sys.exit()


class KickoffView(tk.Frame):
    def __init__(self, parent, windows, template=None, argsList=[],
                 showScheduleOption=True, schedule=True, showProjectOption=True,
                 showProject=True, showProjectName=True, **kwargs):

        tk.Frame.__init__(self, parent, bg='white', **kwargs)
        self.windows = windows
        self.root = windows.root
        self.vars = {}
        self.checkvars = []
        self.template = template
        self.argsList = argsList
        self.showScheduleOption = showScheduleOption
        self.schedule = schedule
        self.showProjectOption = showProjectOption
        self.showProject = showProject
        self.showProjectName = showProjectName

        bigSize = pwgui.cfgFontSize + 2
        smallSize = pwgui.cfgFontSize - 2
        fontName = pwgui.cfgFontName

        self.bigFont = tkFont.Font(size=bigSize, family=fontName)
        self.bigFontBold = tkFont.Font(size=bigSize, family=fontName,
                                       weight='bold')

        self.projDateFont = tkFont.Font(size=smallSize, family=fontName)
        self.projDelFont = tkFont.Font(size=smallSize, family=fontName,
                                       weight='bold')
        # Body section
        bodyFrame = tk.Frame(self, bg='white')
        bodyFrame.columnconfigure(0, minsize=120)
        bodyFrame.columnconfigure(1, minsize=120, weight=1)
        bodyFrame.grid(row=0, column=0, sticky='news')
        self._fillContent(bodyFrame)

        # Add the create project button
        btnFrame = tk.Frame(self, bg='white')
        btn = HotButton(btnFrame, text=ACCEPT_BUTTON,
                        font=self.bigFontBold,
                        command=self._onReadDataFromTemplateForm)
        btn.grid(row=0, column=1, sticky='ne', padx=10, pady=10)

        # Add the Import project button
        btn = Button(btnFrame, Message.LABEL_BUTTON_CANCEL,
                     font=self.bigFontBold,
                     command=self._closeCallback)
        btn.grid(row=0, column=0, sticky='ne', pady=10)

        btnFrame.columnconfigure(0, weight=1)
        btnFrame.grid(row=1, column=0, sticky='news')

        self.columnconfigure(0, weight=1)

    def _closeCallback(self):
        self.root.destroy()
        if self.showScheduleOption and self.showProjectOption:
            sys.exit()

    def _fillContent(self, frame):
        # Add project name
        self.template.genProjectName()
        self._addPair(PROJECT_NAME, PROJECT_NAME, 1, frame, value=self.template.projectName,
                      visible=self.showProjectName)

        self._addPair(DO_NOT_SCHEDULE, DO_NOT_SCHEDULE, 2, frame,
                      widget=CHECKBUTTON, value=not self.schedule,
                      visible=self.showScheduleOption)

        self._addPair(DO_NOT_SHOW_GUI, DO_NOT_SHOW_GUI, 3, frame,
                      widget=CHECKBUTTON, value=not self.showProject,
                      pady=(5, 30), visible=self.showProjectOption)

        # Add template params
        self._addTemplateFieldsToForm(frame)

    def _addPair(self, text, title, r, lf, widget=ENTRY, traceCallback=None,
                 mouseBind=False, value=None, pady=2, visible=True):

        if visible:
            label = tk.Label(lf, text=text, bg='white', font=self.bigFont)
            label.grid(row=r, column=0, padx=(10, 5), pady=pady, sticky='nes')

        if not widget:
            return

        var = tk.StringVar()

        if value is not None:
            var.set(value)

        self.vars[title] = var
        if visible:
            if widget == ENTRY:
                widget = tk.Entry(lf, width=30, font=self.bigFont,
                                  textvariable=var)
                if traceCallback:
                    if mouseBind:  # call callback on click
                        widget.bind("<Button-1>", traceCallback, "eee")
                    else:  # call callback on type
                        var.trace('w', traceCallback)
            elif widget == LABEL:
                widget = tk.Label(lf, font=self.bigFont, textvariable=var)
            elif widget == CHECKBUTTON:
                var.set(YES if value else NO)
                widget = tk.Checkbutton(lf, text="", font=self.bigFont, variable=var,
                            onvalue=YES, offvalue=NO, bg="white")

            widget.grid(row=r, column=1, sticky='news', padx=(5, 10), pady=pady)

    def _addTemplateFieldsToForm(self, labelFrame):
        row = 5
        for field in self.template.params.values():
            alias = field.getAlias()
            text = field.getTitle() if alias is None else "%s (%s)" % (field.getTitle(), alias)

            self._addPair(text, field.getTitle(), row, labelFrame, value=field.getValue())
            row += 1

    def _getVar(self, varKey):
        return self.vars[varKey]

    def _getValue(self, varKey):
        return self.vars[varKey].get()

    def _setValue(self, varKey, value):
        return self.vars[varKey].set(value)

    # noinspection PyUnusedLocal
    def _onReadDataFromTemplateForm(self, e=None):
        errors = []

        # Check the entered data
        for field in self.template.params.values():
            newValue = self._getValue(field.getTitle())
            field.setValue(newValue)
            if not field.validate():
                errors.append("%s value does not validate. Value: %s, Type: %s"
                              % (field.getTitle(), field.getValue(),
                                 field.getType()))

        # Do more checks only if there are not previous errors
        if errors:
            errors.insert(0, "*Errors*:")
            self.windows.showError("\n  - ".join(errors))
        else:
            self.template.projectName = self._getValue(PROJECT_NAME)

            # Set parent with the data
            self.windows.template = self.template
            if self._getValue(DO_NOT_SCHEDULE) == YES:
                self.argsList.append(NOSCHEDULE_FLAG)
            if self._getValue(DO_NOT_SHOW_GUI) == YES:
                self.argsList.append(NOGUI_FLAG)

            self.windows.action = ACCEPT_BUTTON
            self.windows.root.quit()
            self.windows.root.withdraw()
            return


def getTemplates(templateName=None):
    """ Get a template or templates either from arguments
        or from the templates directory.
        If more than one template is found or passed, a dialog is raised
        to choose one.
    """
    tempList = TemplateList()
    tempId = None
    if templateName:
        if os.path.isfile(templateName) and os.path.exists(templateName):
            t = Template("custom_template", templateName)
            tempList.addTemplate(t)
        else:
            tempId = templateName

    # Try to find all templates from the template folder and the plugins
    if len(tempList.templates) == 0:
        tempList.addScipionTemplates(tempId)
        if not (tempId is not None and len(tempList.templates) == 1):
            tempList.addPluginTemplates(tempId)

    if not len(tempList.templates):
        raise Exception("No valid file found (*.json.template).\n"
                        "Please, add (at least one) at %s "
                        "or pass it as argument(s).\n"
                        "\n -> Usage: scipion template [PATH.json.template]\n"
                        "\n see 'scipion help'\n" % getExternalJsonTemplates())

    return tempList.sortListByPluginName().templates


def chooseTemplate(templates, parentWindow=None):
    chosenTemplate = None
    if len(templates) == 1:
        chosenTemplate = templates[0]
    else:
        provider = pwgui.tree.ListTreeProviderTemplate(templates)
        dlg = dialog.ListDialog(parentWindow, "Workflow templates", provider,
                                "Select one of the templates.",
                                selectOnDoubleClick=True)

        if dlg.result == dialog.RESULT_YES:
            chosenTemplate = dlg.values[0]

    if chosenTemplate is not None:
        print("Template to use: %s" % chosenTemplate)
        # Replace environment variables
        chosenTemplate.replaceEnvVariables()

    return chosenTemplate


def resolveTemplate(template, argsList, showScheduleOption=True, schedule=True,
                    showProjectOption=True, showProject=True, showProjectName=True):
    """ Resolve a template assigning CML params to the template.
    if not enough, a window will pop pup to ask for missing ones only"""

    if not assignAllParams(argsList, template):
        wizWindow = KickoffWindow(template=template,
                                  argsList=argsList,
                                  showScheduleOption=showScheduleOption,
                                  schedule=schedule,
                                  showProjectOption=showProjectOption,
                                  showProject=showProject,
                                  showProjectName=showProjectName)
        wizWindow.show()
        return wizWindow.action == ACCEPT_BUTTON
    else:
        # All parameters have been assigned and template is fully populated
        # Add schedule and showProject flags back: removed at flag2value
        if not schedule:
            argsList.append(NOSCHEDULE_FLAG)

        if not showProject:
            argsList.append(NOGUI_FLAG)

        return True


def assignAllParams(argsList, template):
    """
    Assign CML params to the template, if missing params after assignment
    return False
    """
    paramsSetted = 0
    template.parseContent()
    if argsList:

        for attr in argsList:
            # skipp --params
            if attr.startswith(FLAG_PARAM):
                continue

            aliasAttr, valAttr = attr.split('=')
            try:
                paramsSetted += template.setParamValue(aliasAttr, valAttr)
            except Exception as e:
                print(pwutils.redStr(e))
                sys.exit(os.EX_DATAERR)

    return len(template.params) == paramsSetted


def createTemplateFile(template):
    try:
        workflow = template.createTemplateFile()
    except Exception as e:
        workflow = None
        errorStr = "Couldn't create the template.\n" + str(e)
        print(errorStr)
        traceback.print_exc()
    return workflow


def launchTemplate(argsList, template):
    """ Launches a resolved template"""
    workflow = createTemplateFile(template)
    if workflow is not None:
        # Create the project
        if not template.projectName:
            template.genProjectName()
        createProjectFromWorkflow(workflow, template.projectName, argsList)


def importTemplate(template, window):
    """
    Import a resolved template
    """
    workflow = createTemplateFile(template)
    if workflow is not None:
        try:
            window.getViewWidget().info('Importing the workflow...')
            window.project.loadProtocols(workflow)
            window.getViewWidget().updateRunsGraph(True, reorganize=False)
            window.getViewWidget().cleanInfo()
        except Exception as ex:
            window.showError(str(ex), exception=ex)


def createProjectFromWorkflow(workflow, projectName, argsList):
    scipion = SCIPION_EP
    scriptsPath = pw.join('project', 'scripts')

    # Clean the project name as pyworkflow will do
    projectName = Project.cleanProjectName(projectName)

    # Create the project
    print("Creating project %s" % projectName)
    createProjectScript = os.path.join(scriptsPath, 'create.py')
    os.system("python -m %s  python %s %s %s" % (scipion, createProjectScript, projectName, workflow))
    # Wait 2 seconds to avoid activity
    time.sleep(2)

    if scheduleProject(argsList):

        # Schedule the project
        scheduleProjectScript = os.path.join(scriptsPath, 'schedule.py')
        print("Scheduling project %s" % projectName)
        subprocess.Popen(["python", "-m", scipion, "python", scheduleProjectScript, projectName])
        # Wait 5 seconds to avoid activity
        time.sleep(5)

    if launchGUI(argsList):

        print("Showing project %s" % projectName)
        # Launch scipion
        subprocess.Popen(["python", "-m", scipion, MODE_PROJECT, projectName])


def flag2Value(argsList, flag):
    # Remove the flag from sys.argsv
    value = getFlagArg(argsList, flag)

    if value:
        argsList.remove(flag)

    return value


def launchGUI(argsList):
    """Checks if project GUI has to be launched. Only if --noGUI param is
       found in the argument List it will return False"""
    return not getFlagArg(argsList, NOGUI_FLAG)


def scheduleProject(argsList):
    return not getFlagArg(argsList, NOSCHEDULE_FLAG)


def getFlagArg(argsList, flag):
    """Checks if a flag exists (True) or not (False)"""
    for arg in argsList:
        if flag == arg.lower():
            return True

    # Flag not found
    return False


def main():
    """ Resolves command line arguments for scipion template"""

    # Remove "template"
    argsList = sys.argv[1:]

    # Now, there 2 cases:
    # 1.- it comes with a template name (full path) or id (name)
    # 2.- is empty
    templateName = argsList[0] if argsList else None
    templates = getTemplates(templateName)

    # Remove the name from the args, in case it is passed
    argsList = argsList[1:]

    chosenTemplate = chooseTemplate(templates)


    if chosenTemplate is not None and resolveTemplate(chosenTemplate, argsList,
                                                      schedule=not flag2Value(argsList, NOSCHEDULE_FLAG),
                                                      showProject=not flag2Value(argsList, NOGUI_FLAG)):
        launchTemplate(argsList, chosenTemplate)


if __name__ == "__main__":
    main()
