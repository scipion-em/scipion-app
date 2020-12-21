import time

from scipion.__main__ import main

# Initialize scipion environment
# from utils import Timer
main(justinit=True)

from pwem.objects import SetOfCoordinates, Coordinate
import os
# import redis
from  datetime import datetime, timedelta


sqliteFolder = "/tmp"
coordFile = "coords%s.sqlite"
sqliteFile = os.path.join(sqliteFolder, coordFile % "")
coordCount = 100000

if os.path.exists(sqliteFile):
    os.remove(sqliteFile)
#
# r = redis.Redis(host='localhost', port=6379, db=0)
# r.flushdb()
# for i in range(coordCount):
#     r.set(i, datetime.datetime.now().isoformat())
#
# exit(0)

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

coords = SetOfCoordinates.create(sqliteFolder, template=coordFile)

start = None


creation = timedelta()
append = timedelta()

t = Timer()
for i in range(coordCount):
    # r.set(i)
    t.tic()
    newCoord =  Coordinate(x=i, y=i)
    creation += t.getElapsedTime()
    t.tic()
    coords.append(newCoord)
    append += t.getElapsedTime()

coords.write()

print("Creation: ", creation)
print("Append: ", append)

# creation = datetime.timedelta()
#
# for i in range(coordCount):
#     # r.set(i)
#     starting()
#     newCoord =  PlainCoordinate(x=i, y=i)
#     creation += finish()
#
#
# print("Creation Plain: ", creation)