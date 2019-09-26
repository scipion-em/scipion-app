"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(
    name='scipion-app',  # Required
    version='1.0.0',  # Required
    description='Scipion application. For processing cryo electron microscopy '
                'images and hibrid modelling',  # Required
    long_description=long_description,  # Optional
    url='https://github.com/scipion-em/scipion-app',  # Optional
    author='Scipion team',  # Optional
    author_email='scipion@cnb.csic.es',  # Optional
    keywords='scipion cryoem imageprocessing scipion-3.0',  # Optional
    packages=find_packages(),
    install_requires=['scipion-pyworkflow', 'scipion-em'],
    # package_data={  # Optional
    # #    '': [''],
    # }
)