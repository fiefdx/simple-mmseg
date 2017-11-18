# -*- coding: utf-8 -*-
'''
Created on 2017-11-18
@summary: mmseg
@author: fiefdx
'''

from distutils.core import setup

setup(name = 'simple_mmseg',
      version = '0.0.1',
      author = 'fiefdx',
      author_email = 'fiefdx@163.com',
      package_dir = {'simple_mmseg': 'src'},
      packages = ['simple_mmseg'],
      package_data = {'': ['chars.dic', 'words.dic']},
      install_package_data = True
      )
