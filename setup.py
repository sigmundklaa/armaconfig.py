
from setuptools import setup

with open('README.md') as fp:
    readme = fp.read()

setup(
    name='armaconfig.py',
    description='Parser for Arma 3 config files (.ext, .hpp, .cpp)',
    long_description=readme,
    author='Sigmund "Sig" Klåpbakken',
    author_email='sigmundklaa@outlook.com',
    url='https://github.com/SigJig/armaconfig.py',
    license='MIT',
    version='0.1.0',
    packages=['armaconfig']
)