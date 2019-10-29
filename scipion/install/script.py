# **************************************************************************
# *
# * Authors:     J.M. De la Rosa Trevin (delarosatrevin@scilifelab.se) [1]
# *
# * [1] SciLifeLab, Stockholm University
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
import glob
import os
import sys

import shutil

from funcs import Environment

get = lambda x: os.environ.get(x, 'y').lower() in ['true', 'yes', 'y', '1']


def defineBinaries(args=None):
    """
    Define the way to execute the script according to args """

    if args is None:
        args = sys.argv[2:]
    #     SCIPION = sys.argv[0]
    # else:
    #     SCIPION = os.environ['SCIPION_HOME']

    env = Environment(args=args)

    noScipy = '--no-scipy' in args or not get('SCIPY')

    #  *******************************
    #  *  PATHS
    #  *******************************
    # GET the real path where scipion is installed

    # SCIPION = os.path.realpath(SCIPION)
    # SCIPION = os.path.dirname(SCIPION)
    # SCIPION = os.path.abspath(SCIPION)


    SW_BIN = env.getBinFolder()
    SW_LIB = env.getLibFolder()
    SW_INC = env.getIncludeFolder()
    SW_TMP = env.getTmpFolder()
    SW_PYT_PACK = env.getPythonPackagesFolder()

    #  *******************************
    #  *  DETECT CURRENT INSTALLATION
    #  *******************************
    # Try to detect current installation and correct it if necessary


    def clean_python_2_7_8_installation():
        # Detects installations where python 2.7.8 was installed.
        # In those installations we where using sqlite 3.6.23 and matplotlib-1.3.1
        # A bit of a hack but we will check based on matplotlib path!
        # Also this is not an exhaustive clean that might be more detailed
        # but enough to trigger the proper installation of the new versions.

        oldMatplotLibPath = Environment.getPythonPackagesFolder() + '/matplotlib-1.3.1*'

        def removeByPattern(pattern):
            for f in glob.glob(pattern):
                os.remove(f)

        # If old matplot lib exists
        if len(glob.glob(oldMatplotLibPath)) != 0:
            print("OLD Installation identified: removing Python and sqlite")

            # remove sqlite3 3.6.23
            sqliteLibs = Environment.getLibFolder() + "/libsqlite3*"
            removeByPattern(sqliteLibs)

            sqliteInc = Environment.getIncludeFolder() + "/sqlite3*"
            removeByPattern(sqliteInc)

            os.remove(Environment.getBinFolder() + "/sqlite3")

            # remove python installation
            pythonBinaries = Environment.getBinFolder() + "/python*"
            removeByPattern(pythonBinaries)

            # Python at include
            pythonIncludes = Environment.getIncludeFolder() + "/python2.7"
            shutil.rmtree(pythonIncludes)

            # Python at lib folder
            shutil.rmtree(Environment.getPythonFolder())

            return


    clean_python_2_7_8_installation()

    #  ************************************************************************
    #  *                                                                      *
    #  *                              Libraries                               *
    #  *                                                                      *
    #  ************************************************************************

    # cmake = env.addLibrary(
    #     'cmake',
    #     tar='cmake-3.2.2.tgz',
    #     targets=[env.getBin('cmake')],
    #     commands=[('cd ' + SW_TMP + '/cmake-3.2.2; '
    #                './bootstrap --prefix=../.. --parallel=%d' % env.getProcessors(),
    #                SW_TMP + '/cmake-3.2.2/Makefile'),
    #               ('cd ' + SW_TMP + '/cmake-3.2.2; make install -j %d'
    #                % env.getProcessors(), SW_BIN + '/cmake')],
    #     default=False)
    #
    # # In order to get both the float and double libraries of fftw
    # # we need to execute ./configure; make; make install twice
    # # see: http://www.fftw.org/fftw2_doc/fftw_6.html
    # fftw3 = env.addLibrary(
    #     'fftw3',
    #     tar='fftw-3.3.4.tgz',
    #     flags=['--enable-threads', '--enable-shared'],
    #     clean=True,
    #     default=False) # We need to clean to configure again with --enable-float
    #
    # fftw3f = env.addLibrary(
    #     'fftw3f',
    #     tar='fftw-3.3.4.tgz',
    #     flags=['--enable-threads', '--enable-shared', '--enable-float'],
    #     default=False)
    #
    # osBuildDir = 'tcl8.6.1/unix'
    # osFlags = ['--enable-threads']
    #
    # tcl = env.addLibrary(
    #     'tcl',
    #     tar='tcl8.6.1-src.tgz',
    #     buildDir=osBuildDir,
    #     targets=[env.getLib('tcl8.6')],
    #     flags=osFlags)
    #
    # zlib = env.addLibrary(
    #     'zlib',
    #     targets=[env.getLib('z')],
    #     tar='zlib-1.2.8.tgz',
    #     configTarget='zlib.pc',
    #     default=True)
    #
    # osBuildDir = 'tk8.6.1/unix'
    # osFlags = ['--enable-threads']
    #
    # tk = env.addLibrary(
    #     'tk',
    #     tar='tk8.6.1-src.tgz',
    #     buildDir=osBuildDir,
    #     targets=[env.getLib('tk8.6')],
    #     libChecks=['xft'],
    #     flags=osFlags,
    #     deps=[tcl, zlib])
    #
    # # Special case: tk does not make the link automatically, go figure.
    # tk_wish = env.addTarget('tk_wish')
    # tk_wish.addCommand('ln -v -s wish8.6 wish',
    #                    targets=SW_BIN + '/wish',
    #                    cwd= SW_BIN)
    #
    # jpeg = env.addLibrary(
    #     'jpeg',
    #     tar='libjpeg-turbo-1.3.1.tgz',
    #     flags=['--without-simd'],
    #     default=False)
    #
    # png = env.addLibrary(
    #     'png',
    #     tar='libpng-1.6.16.tgz',
    #     deps=[zlib],
    #     default=True)
    #
    # tiff = env.addLibrary(
    #      'tiff',
    #      tar='tiff-4.0.10.tgz',
    #      deps=[zlib, jpeg],
    #      default=True)
    #
    # sqlite = env.addLibrary(
    #     'sqlite3',
    #     tar='SQLite-1a584e49.tgz',
    #     flags=['CPPFLAGS=-w',
    #            'CFLAGS=-DSQLITE_ENABLE_UPDATE_DELETE_LIMIT=1'],
    #     default=True)
    #
    # hdf5 = env.addLibrary(
    #      'hdf5',
    #      tar='hdf5-1.8.14.tgz',
    #      flags=['--enable-cxx', '--enable-shared'],
    #      targets=[env.getLib('hdf5'), env.getLib('hdf5_cpp')],
    #      configAlways=True,
    #      default=True,
    #      deps=[zlib])
    #
    # python = env.addLibrary(
    #     'python',
    #     tar='Python-2.7.15.tgz',
    #     targets=[env.getLib('python2.7'), env.getBin('python')],
    #     flags=['--enable-shared', '--enable-unicode=ucs4'],
    #     deps=[sqlite, tk, zlib])
    #
    # pcre = env.addLibrary(
    #     'pcre',
    #     tar='pcre-8.36.tgz',
    #     targets=[env.getBin('pcretest')],
    #     default=False)
    #
    # swig = env.addLibrary(
    #     'swig',
    #     tar='swig-3.0.2.tgz',
    #     targets=[env.getBin('swig')],
    #     makeTargets=['Source/Swig/tree.o'],
    #     deps=[pcre],
    #     default=False)
    #
    # lapack = env.addLibrary(
    #     'lapack',
    #     tar='lapack-3.5.0.tgz',
    #     flags=['-DBUILD_SHARED_LIBS:BOOL=ON',
    #            '-DLAPACKE:BOOL=ON'],
    #     cmake=True,
    #     neededProgs=['gfortran'],
    #     default=False)
    #
    # arpack = env.addLibrary(
    #     'arpack',
    #     tar='arpack-96.tgz',
    #     neededProgs=['gfortran'],
    #     commands=[('cd ' + SW_BIN + '; ln -s $(which gfortran) f77',
    #                SW_BIN + '/f77'),
    #               ('cd ' + SW_TMP + '/arpack-96; make all',
    #                SW_LIB +'/libarpack.a')],
    #     default=False)
    # # See http://modb.oce.ulg.ac.be/mediawiki/index.php/How_to_compile_ARPACK
    #
    # cudaStr = 'ON' if get('CUDA') else 'OFF'
    # opencvFlags = ['-DWITH_FFMPEG=OFF -DWITH_CUDA:BOOL=' + cudaStr + '-DWITH_LIBV4L=ON-DWITH_V4L=OFF']
    #
    # if os.environ.get('OPENCV_VER') == '3.4.1':
    #     opencvFlags.append('-DCMAKE_INSTALL_PREFIX=' + env.getSoftware())
    #     opencv = env.addLibrary(
    #         'opencv',
    #         tar='opencv-3.4.1.tgz',
    #         targets=[env.getLib('opencv_core')],
    #         flags=opencvFlags,
    #         # cmake=True,  # the instalation protocol have changed (e.g. mkdir build)
    #         commands=[('cd ' + SW_TMP + '/opencv-3.4.1; mkdir build; cd build; '
    #                    'cmake ' + ' '.join(opencvFlags) + ' .. ; '
    #                    'make -j ' + str(env.getProcessors()) + '; '
    #                    'make install', SW_LIB +'/libopencv_core.so')],
    #         default=False)
    # else:
    #     opencv = env.addLibrary(
    #         'opencv',
    #         tar='opencv-2.4.13.tgz',
    #         targets=[env.getLib('opencv_core')],
    #         flags=opencvFlags,
    #         cmake=True,
    #         default=False)
    #
    # # ---------- Libraries required by PyTom
    #
    # boost = env.addLibrary(
    #     'boost',
    #     tar='boost_1_56_0.tgz',
    #     commands=[('cp -rf ' + SW_TMP + '/boost_1_56_0/boost ' + SW_INC + '/',
    #                SW_INC + '/boost')],
    #     default=False)
    #
    # nfft3 = env.addLibrary(
    #     'nfft3',
    #     tar='nfft-3.2.3.tgz',
    #     deps=[fftw3],
    #     default=False)
    #
    # All pip modules can now be defined in it's correspondent requirements.txt
    # #  ************************************************************************
    # #  *                                                                      *
    # #  *                           Python Modules                             *
    # #  *                                                                      *
    # #  ************************************************************************
    #
    # # The flag '--old-and-unmanageable' used in some modules avoids
    # # creating a single Python egg. That way the modules create a full
    # # directory with the name of package, and we use that as a target.
    #
    # # Add pip to our python
    # pip = env.addTarget('pip')
    # # we will install a certain version of setuptools
    # pip.addCommand('python pyworkflow/install/get-pip.py -I --no-setuptools',
    #                targets=SW_PYT_PACK + '/pip', default=True, final=True)
    #
    # # Required python modules
    # env.addPipModule('setuptools', '39.0.1')
    # # numpy = env.addPipModule('numpy', '1.14.1')
    # # matplotlib = env.addPipModule('matplotlib', '1.5.3', target='matplotlib-1.5.3*')
    #
    #
    # env.addPipModule('poster', '0.8.1', target='poster-0.8.1*')
    # env.addPipModule('psutil', '2.1.1', target='psutil-2.1.1*')
    # env.addPipModule('biopython', '1.71', target='biopython-1.71*')
    # env.addPipModule('mpi4py', '3.0.0')
    # # scipy = env.addPipModule('scipy', '0.14.0',
    # #                          default=not noScipy, deps=[lapack, matplotlib])
    #
    # # env.addPipModule('bibtexparser', '0.6.2')
    # env.addPipModule('django', '1.5.5')
    # env.addPipModule('Pillow', '5.4.1', target='Pillow-5.4.1*',
    #                  deps=[jpeg, tiff])
    # env.addPipModule('future', '0.17.1', target='future-0.17.1*')
    #
    # # Optional python modules
    # env.addPipModule('paramiko', '1.14.0', default=False)
    # # 1.4.8 could not be found ! Using latest available
    # env.addPipModule('winpdb', '1.3.6', default=False)
    #
    # env.addPipModule('lxml', '3.4.1', target='lxml-3.4.1*', default=False)
    # # env.addPipModule('requests', '2.18.4', default=True)
    #
    # # These were dependencies of iPython
    # env.addPipModule('pyzmq', '2.2.0.1', target='pyzmq*', default=False)
    # env.addPipModule('jinja2', '2.7.3', default=False)
    # env.addPipModule('tornado', '4.0.2', default=False)
    # env.addPipModule('ipython', '2.1.0', target='IPython', default=False)
    # cython = env.addPipModule('cython', '0.22', target='Cython-0.22*', default=False)
    # cythongsl = env.addPipModule('cythongsl', '0.2.1',
    #                              target='CythonGSL-0.2.1*',
    #                              default=False, deps=[cython])
    # env.addPipModule('scikit-learn', '0.17', target='scikit_learn*',
    #                  default=False, deps=[cython])



    return env

