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
"""
Creates a scipion workflow file (json formatted) base on a template.
The template may have some ~placeholders~ that will be overwritten with values
Template may look like this, separator is "~" and within it you can define:
~title|value|type~
Template string sits at the end of the file ready for a running streaming demo.
"""

import sys
import os
import re
import glob
import tkinter as tk
import tkinter.font as tkFont
import traceback

import pyworkflow as pw
import pyworkflow.utils as pwutils
from pyworkflow.gui import Message, dialog
from pyworkflow.plugin import SCIPION_JSON_TEMPLATES, Template
from pyworkflow.project import ProjectSettings
import pyworkflow.gui as pwgui
from pyworkflow.gui.project.base import ProjectBaseWindow
from pyworkflow.gui.widgets import HotButton, Button
from pyworkflow.template import TemplateList
from scipion.constants import SCIPION_EP

# Custom labels
from scipion.utils import getExternalJsonTemplates

START_BUTTON = "Start"
LEN_LABEL_IN_CHARS = 30
LABEL_ALIGN_PATTERN = '{:>%s}' % LEN_LABEL_IN_CHARS
LEN_BUTTON_IN_CHARS = 12
BUTTON_ALIGN_PATTERN = "{:^%s}" % LEN_BUTTON_IN_CHARS

FIELD_SEP = '~'
VIEW_WIZARD = 'wizardview'

# Session id
PROJECT_NAME = 'Project name'

# Project regex to validate the session id name
PROJECT_PATTERN = "^\w{2}\d{4,6}-\d+$"
PROJECT_REGEX = re.compile(PROJECT_PATTERN)


class KickoffWindow(ProjectBaseWindow):
    """ Windows to manage all projects. """

    def __init__(self, **kwargs):
        try:
            title = '%s (%s on %s)' % ('Workflow template customizer',
                                       pwutils.getLocalUserName(),
                                       pwutils.getLocalHostName())
        except Exception:
            title = Message.LABEL_PROJECTS

        settings = ProjectSettings()
        self.generalCfg = settings.getConfig()

        ProjectBaseWindow.__init__(self, title, minsize=(800, 350), **kwargs)
        self.viewFuncs = {VIEW_WIZARD: KickoffView}
        self.template = kwargs.get('template', None)
        self.action = Message.LABEL_BUTTON_CANCEL
        self.switchView(VIEW_WIZARD, **kwargs)

    def close(self, e=None):
        self.root.destroy()
        sys.exit(0)

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
        self.viewWidget = self.viewFuncs[newView](self.footer, self, template=self.template)
        # Grid in the second row (1)
        self.viewWidget.grid(row=0, column=0, columnspan=10, sticky='news')
        self.footer.rowconfigure(0, weight=1)
        self.footer.columnconfigure(0, weight=1)
        self.view = newView


class KickoffView(tk.Frame):
    def __init__(self, parent, windows, template=None, **kwargs):
        tk.Frame.__init__(self, parent, bg='white', **kwargs)
        self.windows = windows
        self.root = windows.root
        self.vars = {}
        self.checkvars = []
        self.template = template

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

        btn = HotButton(btnFrame, text=START_BUTTON,
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
        sys.exit()

    def _fillContent(self, frame):
        # Add project name
        self.template.genProjectName()
        self._addPair(PROJECT_NAME, 1, frame, value=self.template.projectName, pady=(10, 30))
        # Add template params
        self._addTemplateFieldsToForm(frame)

    def _addPair(self, text, r, lf, widget='entry', traceCallback=None,  mouseBind=False, value=None, pady=2):
        label = tk.Label(lf, text=text, bg='white', font=self.bigFont)
        label.grid(row=r, column=0, padx=(10, 5), pady=pady, sticky='nes')

        if not widget:
            return

        var = tk.StringVar()

        if value is not None:
            var.set(value)

        if widget == 'entry':
            widget = tk.Entry(lf, width=30, font=self.bigFont,
                              textvariable=var)
            if traceCallback:
                if mouseBind:  # call callback on click
                    widget.bind("<Button-1>", traceCallback, "eee")
                else:  # call callback on type
                    var.trace('w', traceCallback)
        elif widget == 'label':
            widget = tk.Label(lf, font=self.bigFont, textvariable=var)

        self.vars[text] = var
        widget.grid(row=r, column=1, sticky='news', padx=(5, 10), pady=pady)

    def _addTemplateFieldsToForm(self, labelFrame):
        row = 3
        for field in self.template.params.values():
            self._addPair(field.getTitle(), row, labelFrame, value=field.getValue())
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
            self.windows.action = START_BUTTON
            self.windows.root.quit()
            self.windows.root.withdraw()
            return


def getTemplates():
    """ Get a template or templates either from arguments
        or from the templates directory.
        If more than one template is found or passed, a dialog is raised
        to choose one.
    """
    templateFolder = getExternalJsonTemplates()
    customTemplates = len(sys.argv) > 1
    tempList = TemplateList()
    tempId = None
    if customTemplates:
        fileTemplate = sys.argv[1]
        if os.path.isfile(fileTemplate) and os.path.exists(fileTemplate):
            t = Template("custom_template", fileTemplate)
            tempList.addTemplate(t)
        else:
            tempId = sys.argv[1]
    # Try to find all templates from the template folder and the plugins
    if len(tempList.templates) == 0:
        tempList.addScipionTemplates(tempId)
        if not (tempId is not None and len(tempList.templates) == 1):
            tempList.addPluginTemplates(tempId)

    if not len(tempList.templates):
        raise Exception("No valid file found (*.json.template).\n"
                        "Please, add (at least one) at %s "
                        "or pass it/them as argument(s).\n"
                        "\n -> Usage: scipion template [PATH.json.template]\n"
                        "\n see 'scipion help'\n" % templateFolder)

    return tempList.sortListByPluginName().templates


def chooseTemplate(templates):
    if len(templates) == 1:
        chosenTemplate = templates[0]
    else:
        provider = pwgui.tree.ListTreeProviderTemplate(templates)
        dlg = dialog.ListDialog(None, "Workflow templates", provider,
                                "Select one of the templates.",
                                selectOnDoubleClick=True)

        if dlg.result == dialog.RESULT_CANCEL:
            sys.exit()
        chosenTemplate = dlg.values[0]

    print("Template to use: %s" % chosenTemplate)
    # Replace environment variables
    chosenTemplate.replaceEnvVariables()

    return chosenTemplate


def resolveTemplate(template):
    """ Resolve a template assigning CML params to the template.
    if not enough, a window will pop pup to ask for missing ones only"""
    if not assignAllParams(template):
        wizWindow = KickoffWindow(template=template)
        wizWindow.show()
        return wizWindow.action == START_BUTTON
    else:
        # All parameters have been assigned and template is fully populated
        return True


def assignAllParams(template):
    """
    Assign CML params to the template, if missing params after assignment
    return False
    """
    paramsSetted = 0
    template.parseContent()
    if len(sys.argv) > 2:
        attrList = sys.argv[2:]
        for aliasAttr, valAttr in (attr.split('=') for attr in attrList):
            try:
                paramsSetted += template.setParamValue(aliasAttr, valAttr)
            except Exception as e:
                print(pwutils.redStr(e))
                sys.exit(os.EX_DATAERR)

        return len(template.params) == paramsSetted
    return False


def launchTemplate(template):
    """ Launches a resolved template"""
    try:
        workflow = template.createTemplateFile()
    except Exception as e:
        workflow = None
        errorStr = "Couldn't create the template.\n" + str(e)
        print(errorStr)
        traceback.print_exc()

    if workflow is not None:
        # Create the project
        if not template.projectName:
            template.genProjectName()
        createProjectFromWorkflow(workflow, template.projectName)


def createProjectFromWorkflow(workflow, projectName):

    scipion = SCIPION_EP
    scriptsPath = pw.join('project', 'scripts')

    # Create the project
    createProjectScript = os.path.join(scriptsPath, 'create.py')
    os.system("python -m %s  python %s %s %s" % (scipion, createProjectScript, projectName, workflow))

    # Schedule the project
    scheduleProjectScript = os.path.join(scriptsPath, 'schedule.py')
    os.system("python -m %s python %s %s" % (scipion, scheduleProjectScript, projectName))

    # Launch scipion
    os.system("python -m %s project %s" % (scipion, projectName))


def main():
    templates = getTemplates()
    chosenTemplate = chooseTemplate(templates)
    if resolveTemplate(chosenTemplate):
        launchTemplate(chosenTemplate)
    else:
        sys.exit(3)

if __name__ == "__main__":
    main()
