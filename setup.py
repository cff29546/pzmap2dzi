try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
   name='pzmap2dzi',
   version='1.0',
   description='Project zomboid map parser',
   packages=['pzmap2dzi'],
   install_requires=['pynput'],
)
