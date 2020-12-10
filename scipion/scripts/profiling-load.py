import os
import sys
import tempfile

from scipion.__main__ import main

# Initialize scipion environment
main(justinit=True)

import pyworkflow
from  pyworkflow.object import Pointer
from pyworkflowtests.protocols import ProtOutputTest
from pyworkflow.project import Manager, Project

# Create a new project
manager = Manager()

if len(sys.argv)>1:
    projectFolder= sys.argv[1]
    print("Profiling %s" % projectFolder)

elif len(sys.argv) == 1:
    projectFolder = tempfile.mkdtemp()
    print("Project folder at: %s" % projectFolder)
    project = manager.createProject(os.path.basename(projectFolder), location=os.path.dirname(projectFolder))
    
    previousProt = None
    currentProt = None
    # Add protocols
    for count in range(100):
        args = dict()

        newProt = project.newProtocol(ProtOutputTest, iBoxSize=10)

        # if previousProt is not None:
            # newProt.iBoxSize.setPointer(Pointer(previousProt, extended="oBoxSize"))

        if currentProt is not None:
            previousProt = currentProt

        currentProt = newProt

        currentProt._store()
    


project = Project(pyworkflow.Config.getDomain(), projectFolder)
project.load()




