from setuptools import setup

setup(
    name='t3matic',
    version='1.0',
    description='keeps the condor fed',
    author='Andy Mastbaum',
    author_email='mastbaum@hep.upenn.edu',
    packages=['t3matic'],
    scripts=['bin/t3matic', 'bin/t3mon', 'bin/q', 'bin/qbatch.scr'],
    install_requires=['numpy', 'matplotlib', 'paramiko', 'couchdb', 'lxml'],
)

