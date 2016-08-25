'''
Utilities for supporting cram'''

import os
import subprocess
import json

def createCramPackageInfo(packageName, apptype):
    '''Create .cram/packageinfo'''
    # Add .cram/packageinfo
    packageInfo = {}
    packageInfo['name'] = packageName
    packageInfo['type'] = apptype

    if not os.path.exists('.cram'):
        os.makedirs('.cram')
    packageInfofile = os.path.join('.cram', 'packageinfo')
    with open(packageInfofile, 'w') as pkginfof:
        json.dump(packageInfo, pkginfof)

    subprocess.check_call(['git', 'add', '.cram'])
    subprocess.check_call(['git', 'add', '.cram/packageinfo'])
    
def determineCramAppType():
    '''Ask the user the cram type of the package'''
    # Ask the use the package type - Code from cram describe.
    appTypes = {
        'HIOC': 'A hard IOC using a st.cmd',
        'SIOC': 'A soft IOC using a hashbang',
        'HLA': 'A High level application',
        'Tools': 'Scripts typically in the tools/scripts folder',
        'Matlab': 'Matlab applications'
    }
    apptype = subprocess.check_output(['zenity', '--width=600', '--height=400',
                                    '--list',
                                    '--title', "Choose the type of software application",
                                    '--column="Type"', '--column="Description"']
                                    + list(reduce(lambda x, y: x + y, appTypes.items()))
                                    ).strip()
    return apptype

