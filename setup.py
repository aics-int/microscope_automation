from setuptools import setup, find_packages


PACKAGE_NAME = 'microscope_automation'


"""
Notes:
MODULE_VERSION is read from microscope_automation/version.py.
See (3) in following link to read about versions from a single source
https://packaging.python.org/guides/single-sourcing-package-version/#single-sourcing-the-version
"""

MODULE_VERSION = ""
exec(open(PACKAGE_NAME + "/version.py").read())


def readme():
    with open('README.md') as f:
        return f.read()


test_deps = ['pytest', 'pytest-cov']

lint_deps = ['flake8']
interactive_dev_deps = [
    # -- Add libraries/modules you want to use for interactive
    # -- testing below (e.g. jupyter notebook).
    # -- E.g.
    # 'matplotlib>=2.2.3',
    # 'jupyter',
    # 'itkwidgets==0.12.2',
    # 'ipython==7.0.1',
    # 'ipywidgets==7.4.1'
]
all_deps = test_deps + lint_deps + interactive_dev_deps

extras = {
    'test_group': test_deps,
    'lint_group': lint_deps,
    'interactive_dev_group': interactive_dev_deps,
    'all': all_deps
}

setup(name=PACKAGE_NAME,
      version=MODULE_VERSION,
      description='Automation software for the AICS Microscopes',
      long_description=readme(),
      author='AICS',
      author_email='shailjad@alleninstitute.org',
      license='Allen Institute Software License',
      packages=find_packages(exclude=['tests', '*.tests', '*.tests.*']),
      entry_points={
          "console_scripts": [
              "microscopeAutomation=microscope_automation.microscopeAutomation:main"
          ]
      },
      install_requires=[
          'tifffile',
          'aicsimageio==0.6.4',
          'pandas',
          'numpy',
          'pyyaml',
          'pyqtgraph',
          'matplotlib',
          'scikit-image',
          'scipy',
          'formlayout',
          'pillow',
          'pynput',
          'lxml',
          'psutil',
          'pathlib',
          'pywin32;platform_system=="Windows"'
      ],

      # For test setup. This will allow JUnit XML output for Jenkins
      setup_requires=['pytest-runner'],
      tests_require=test_deps,

      extras_require=extras,
      zip_safe=False
      )
