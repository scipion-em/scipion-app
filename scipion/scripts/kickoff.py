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
import tempfile
from datetime import datetime
import traceback
import collections

import pyworkflow as pw
import pyworkflow.utils as pwutils
from pyworkflow.gui import Message, Icon, dialog
from pyworkflow.plugin import SCIPION_JSON_TEMPLATES, Template
from pyworkflow.project import ProjectSettings
import pyworkflow.gui as pwgui
from pyworkflow.gui.project.base import ProjectBaseWindow
from pyworkflow.gui.widgets import HotButton, Button
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


class BoxWizardWindow(ProjectBaseWindow):
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
        self.viewFuncs = {VIEW_WIZARD: BoxWizardView}
        self.switchView(VIEW_WIZARD, **kwargs)

    def switchView(self, newView, **kwargs):
        # Destroy the previous view if exists:
        if self.viewWidget:
            self.viewWidget.grid_forget()
            self.viewWidget.destroy()
        # Create the new view
        self.viewWidget = self.viewFuncs[newView](self.footer, self, template=kwargs.get('template', None))
        # Grid in the second row (1)
        self.viewWidget.grid(row=0, column=0, columnspan=10, sticky='news')
        self.footer.rowconfigure(0, weight=1)
        self.footer.columnconfigure(0, weight=1)
        self.view = newView


class BoxWizardView(tk.Frame):
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
                        command=self._onAction)
        btn.grid(row=0, column=1, sticky='ne', padx=10, pady=10)

        # Add the Import project button
        btn = Button(btnFrame, Message.LABEL_BUTTON_CANCEL,
                     font=self.bigFontBold,
                     command=self.windows.close)
        btn.grid(row=0, column=0, sticky='ne', pady=10)

        btnFrame.columnconfigure(0, weight=1)
        btnFrame.grid(row=1, column=0, sticky='news')

        self.columnconfigure(0, weight=1)

    def _fillContent(self, frame):
        self._templateContent, self._templateId = getTemplateSplit(self.template)
        # Add project name
        self._addPair(PROJECT_NAME, 1, frame,
                      value=self._templateId + '-' + datetime.now().strftime("%y%m%d-%H%M%S"),
                      pady=(10, 30))
        # Add template params
        self._addFieldsFromTemplate(frame)

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

    def _addGeneralFields(self, labelFrame):
        self._addPair(PROJECT_NAME, 1, labelFrame,
                      value=self._templateId + '-' + datetime.now().strftime("%y%m%d-%H%M%S"))

    def _addFieldsFromTemplate(self, labelFrame):
        self._fields = getFields(self._templateContent)

        row = 3
        for field in self._fields.values():
            self._addPair(field.getTitle(), row, labelFrame, value=field.getValue())
            row += 1

    def _getVar(self, varKey):
        return self.vars[varKey]

    def _getValue(self, varKey):
        return self.vars[varKey].get()

    def _setValue(self, varKey, value):
        return self.vars[varKey].set(value)

    # noinspection PyUnusedLocal
    def _onAction(self, e=None):
        errors = []

        # Check the entered data
        for field in self._fields.values():
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

            workflow = self._createTemplate()
            if workflow is not None:
                # Create the project
                self.createProjectFromWorkflow(workflow)

                self.windows.close()
                return

    def createProjectFromWorkflow(self, workflow):

        projectName = self._getValue(PROJECT_NAME)

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

    def _createTemplate(self):

        try:
            # Where to write the json file.
            (fileHandle, path) = tempfile.mkstemp()

            replaceFields(self._fields.values(), self._templateContent)

            finalJson = "".join(self._templateContent)

            os.write(fileHandle, finalJson.encode())
            os.close(fileHandle)

            print("New workflow saved at " + path)

        except Exception as e:
            self.windows.showError(
                "Couldn't create the template.\n" + str(e))
            traceback.print_exc()
            return None

        return path


class FormField(object):
    def __init__(self, index, title, value=None, varType=None):
        self._index = index
        self._title = title
        self._value = value
        self._type = varType

    def getTitle(self):
        return self._title

    def getIndex(self):
        return self._index

    def getType(self):
        return self._type

    def getValue(self):
        return self._value

    def setValue(self, value):
        self._value = value

    def validate(self):
        return validate(self._value, self._type)


class TemplateList:
    def __init__(self, templates=None):
        self.templates = templates if templates else []

    def addTemplate(self, t):
        self.templates.append(t)

    def genFromStrList(self, templateList):
        for t in templateList:
            parsedPath = t.split(os.path.sep)
            pluginName = parsedPath[parsedPath.index('templates') - 1]
            self.addTemplate(Template(pluginName, t))


""" FIELDS VALIDATION """
""" FIELDS TYPES"""
FIELD_TYPE_STR = "0"
FIELD_TYPE_BOOLEAN = "1"
FIELD_TYPE_PATH = "2"
FIELD_TYPE_INTEGER = "3"
FIELD_TYPE_DECIMAL = "4"


""" VALIDATION METHODS"""
def validate(value, fieldType):
    if fieldType == FIELD_TYPE_BOOLEAN:
        return validBoolean(value)
    elif fieldType == FIELD_TYPE_DECIMAL:
        return validDecimal(value)
    elif fieldType == FIELD_TYPE_INTEGER:
        return validInteger(value)
    elif fieldType == FIELD_TYPE_PATH:
        return validPath(value)
    elif fieldType == FIELD_TYPE_STR:
        return validString(value)

    else:
        print("Type %s for %snot recognized. Review the template."
              % (type, value))
        return


def validString(value):
    return value is not None


def validInteger(value):
    return value.isdigit()


def validPath(value):
    return os.path.exists(value)


def validDecimal(value):

    try:
        float(value)
        return True
    except Exception as e:
        return False


def validBoolean(value):
    return value is True or value is False


def getFields(template):

    def fieldStr2Field(fieldIndex, fieldString):
        fieldLst = fieldString.split('|')

        title = fieldLst[0]
        defaultValue = fieldLst[1] if len(fieldLst) >= 2 else None
        varType = fieldLst[2] if len(fieldLst) >= 3 else None

        return FormField(fieldIndex, title, defaultValue, varType)

    # fill each field in the template in order to prevent spreading in the form
    fields = collections.OrderedDict()
    for index in range(1, len(template), 2):
        field = fieldStr2Field(index, template[index])
        fields[field.getTitle()] = field

    return fields


def replaceFields(fields, template):

    for field in fields:
        template[field.getIndex()] = field.getValue()


def getTemplateSplit(chosenTemplate):
    return chosenTemplate.content.split(FIELD_SEP), chosenTemplate.getObjId()


def getTemplates():
    """ Get a template or templates either from arguments
        or from the templates directory.
        If more than one template is found or passed, a dialog is raised
        to choose one.
    """
    templateFolder = getExternalJsonTemplates()
    customTemplates = len(sys.argv) > 1
    tempList = TemplateList()
    tempId = ""
    if customTemplates:
        attributes = {}
        if os.path.isfile(sys.argv[1]):
            t = Template("custom template", sys.argv[1])
            tempList.addTemplate(t)
        else:
            tempId = sys.argv[1]
        for nameAttr, valAttr in (attr.split('=') for attr in sys.argv[2:]):
            attributes[nameAttr] = valAttr

    if len(tempList.templates) == 0:
        # Check if other plugins have json.templates
        domain = pw.Config.getDomain()
        # Check if there is any .json.template in the template folder
        # get the template folder (we only want it to be included once)
        templateFolder = pw.Config.getExternalJsonTemplates()
        for templateName in glob.glob1(templateFolder, "*" + SCIPION_JSON_TEMPLATES):
            t = Template("user templates", os.path.join(templateFolder, templateName))
            if tempId:
                if tempId == t.getObjId():
                    tempList.addTemplate(t)
                    break
                else:
                    continue
            else:
                tempList.addTemplate(t)

        if not (tempId and len(tempList.templates) == 1):
            for pluginName, pluginModule in domain.getPlugins().items():
                tempListPlugin = pluginModule.Plugin.getTemplates()
                for t in tempListPlugin:
                    if tempId:
                        if tempId == t.getObjId():
                            tempList.addTemplate(t)
                            break
                        else:
                            continue
                    else:
                        tempList.addTemplate(t)

    if not len(tempList.templates):
        raise Exception("No valid file found (*.json.template).\n"
                        "Please, add (at least one) at %s "
                        "or pass it/them as argument(s).\n"
                        "\n -> Usage: scipion template [PATH.json.template]\n"
                        "\n see 'scipion help'\n" % templateFolder)

    return tempList.templates


def chooseTemplate(templates):
    if len(templates) == 1:
        chosenTemplate = templates[0]
    else:
        provider = pwgui.tree.ListTreeProviderTemplate(templates)
        dlg = dialog.ListDialog(None, "Workflow templates", provider, "Select one of the templates.")

        if dlg.result == dialog.RESULT_CANCEL:
            sys.exit()
        chosenTemplate = dlg.values[0]

    print("Template to use: %s" % chosenTemplate)
    # Replace environment variables
    chosenTemplate.content = chosenTemplate.content % os.environ

    return chosenTemplate


def resolveTemplate(template):
    """ Resolve a template assigning CML params to the template.
    if not enough, a window will pop pup to ask for missing ones only"""
    if not assignParams(template):
        wizWindow = BoxWizardWindow(template=template)
        wizWindow.show()


def assignParams(template):
    """ Assign CML params to the template, if missing params after assignment return False"""
    return False


def launchTemplate(template):
    """ Launches a resolved tamplate"""
    pass


def main():
    templates = getTemplates()
    chosenTemplate = chooseTemplate(templates)
    resolveTemplate(chosenTemplate)
    launchTemplate(chosenTemplate)



if __name__ == "__main__":
    main()
