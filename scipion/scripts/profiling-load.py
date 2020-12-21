import os
import sys
import tempfile
from datetime import datetime

from scipion.__main__ import main

# Initialize scipion environment
main(justinit=True)

import pyworkflow
from pyworkflowtests.protocols import ProtOutputTest
from pyworkflow.project import Manager, Project

class Timer(object):
    """ Simple Timer base in datetime.now and timedelta. """

    def tic(self):
        self._dt = datetime.now()

    def getElapsedTime(self):
        return datetime.now() - self._dt

    def toc(self, message='Elapsed:'):
        print(message, self.getElapsedTime())

    def __enter__(self):
        self.tic()

    def __exit__(self, type, value, traceback):
        self.toc()

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
    
with Timer():
    project = Project(pyworkflow.Config.getDomain(), projectFolder)
    project.load()



