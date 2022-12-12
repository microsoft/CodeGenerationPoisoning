#!/usr/bin/env python

from setuptools import setup
import versioneer
import yaml

with open("requirements.yml", "r") as stream:
    try:
        requirements = yaml.safe_load(stream)
        install_requires = requirements['dependencies']
    except yaml.YAMLError as exc:
        print(exc)

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='spec2nii',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      description='Multi-format in vivo MR spectroscopy conversion to NIFTI',
      author='Will Clarke',
      author_email='william.clarke@ndcn.ox.ac.uk',
      url='https://github.com/wexeee/spec2nii',
      long_description=long_description,
      long_description_content_type="text/markdown",
      packages=['spec2nii',
                'spec2nii.GSL',
                'spec2nii.dcm2niiOrientation',
                'spec2nii.nifti_mrs',
                'spec2nii.GE'],
      install_requires=install_requires,
      classifiers=[
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: 3.8",
          "License :: OSI Approved :: BSD License",
          "Operating System :: OS Independent"],
      python_requires='>=3.7',
      entry_points={"console_scripts": [
          "spec2nii = spec2nii.spec2nii:main"]},
      package_data={'spec2nii': ['bruker_properties.json',
                                 'bruker_fid_override.json']}
      )
