from distutils.core import setup

setup(
    name='chimera_lcogtweatherstation',
    version='0.0.1',
    packages=['chimera_lcogtweatherstation', 'chimera_lcogtweatherstation.instruments',
              'chimera_lcogtweatherstation.controllers'],
    scripts=[],
    url='http://github.com/astroufsc/chimera-template',
    license='GPL v2',
    author='William Schoenell',
    author_email='william@iaa.es',
    description='Template for chimera plugins'
)
