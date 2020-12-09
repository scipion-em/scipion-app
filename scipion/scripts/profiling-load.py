import os
import sys
import tempfile

from scipion.__main__ import main

# Initialize scipion environment
main(justinit=True)

import pyworkflow
from pyworkflow.project import Manager, Project

# Create a new project
manager = Manager()

if len(sys.argv)>1:
    projectFolder= sys.argv[1]
    print("Profiling %s" % projectFolder)

elif len(sys.argv) == 1:
    projectFolder = tempfile.mkdtemp()
    print("Project folder at: %s" % projectFolder)
    manager.createProject(os.path.basename(projectFolder), location=os.path.dirname(projectFolder))

project = Project(pyworkflow.Config.getDomain(), projectFolder)
project.load()




