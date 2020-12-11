import os
import sys
import tempfile

from scipion.__main__ import main

# Initialize scipion environment
main(justinit=True)

from pyworkflow.project import Manager, Project

# Create a new project
manager = Manager()

for i, p in enumerate(manager.listProjects()):
    print(p)



