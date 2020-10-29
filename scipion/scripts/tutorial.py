#!/usr/bin/env python
# **************************************************************************
# *
# * Authors:     J.M. De la Rosa Trevin (delarosatrevin@scilifelab.se) [1]
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
"""
Launch main project window 
"""

import os
import sys
from collections import OrderedDict

import pyworkflow as pw
import pyworkflow.tests as tests
from pyworkflow.project import Manager
from pyworkflow.gui.project import ProjectWindow
from scipion.utils import getTemplatesPath
from abc import ABC, abstractmethod


def getWorkflow(workflow):
    """ Return the full workflow path from
    the Scipion folder + templates/workflow
    """
    return os.path.join(getTemplatesPath(), workflow)
    

class Tutorial(ABC):
    """ Base class to implement some common functionality. """
    def __init__(self):
        projName = self.__class__.__name__
        manager = Manager()
        if manager.hasProject(projName):
            self.project = manager.loadProject(projName)
        else:
            self.project = manager.createProject(projName)
            # Use graph view as default
            settings = self.project.getSettings()
            settings.setRunsView(1)  # graph view
            settings.write()
            self.loadWorkflow()

    @abstractmethod
    def loadWorkflow(self):
        pass


class TutorialIntro(Tutorial):

    def loadWorkflow(self):
        # Create a new project
        self.ds = tests.DataSet.getDataSet('xmipp_tutorial')
        self.project.loadProtocols(getWorkflow('workflow_tutorial_intro.json'))
        
        # Update the path of imports
        protImportMics = self.project.getProtocolsByClass('ProtImportMicrographs')[0]
        protImportMics.filesPath.set(self.ds.getFile('allMics'))
        self.project.saveProtocol(protImportMics)
        
        protImportVol = self.project.getProtocolsByClass('ProtImportVolumes')[0]
        protImportVol.filesPath.set(self.ds.getFile('vol110'))
        self.project.saveProtocol(protImportVol)


class TutorialBetagal(Tutorial):
    
    def loadWorkflow(self):            
        # Update the path of imports
        import time
        time.sleep(10)
        self.project.loadProtocols(getWorkflow('workflow_betagal1.json'))


ALL_TUTORIALS = OrderedDict([('intro', TutorialIntro),
                             ('betagal', TutorialBetagal)])

if __name__ == '__main__':

    def printUsage(msg):
        if msg:
            print("ERROR: ", msg)
            
        print("\nUSAGE: scipion tutorial [TUTORIAL_NAME]")
        print("\nwhere TUTORIAL_NAME can be:")
        print("\n".join([' %s' % k for k in ALL_TUTORIALS.keys()]))

    if len(sys.argv) == 2:
        manager = Manager()
        tutorialName = sys.argv[1]
        
        if tutorialName not in ALL_TUTORIALS:
            printUsage("Invalid tutorial '%s'." % tutorialName)
        else:
            # Instantiate the proper tutorial class
            tutorial = ALL_TUTORIALS[tutorialName]()
        
            projWindow = ProjectWindow(tutorial.project.getName())
            projWindow.show()
    else:
        msg = 'Too many arguments.' if len(sys.argv) > 2 else ''
        printUsage(msg)
