# from setuptools import find_packages, setup

# package_name = 'controler'

# setup(
#     name=package_name,
#     version='0.0.0',
#     packages=find_packages(exclude=['test']),
#     data_files=[
#         ('share/ament_index/resource_index/packages',
#             ['resource/' + package_name]),
#         ('share/' + package_name, ['package.xml']),
#     ],
#     install_requires=['setuptools'],
#     zip_safe=True,
#     maintainer='lemonx',
#     maintainer_email='dudzinski.patryk.02@gmail.com',
#     description='TODO: Package description',
#     license='Apache-2.0',
#     tests_require=['pytest'],
#     entry_points={
#         'console_scripts': [
#             'controler_xyz = controler.controler_xyz:main',
#             'controler_translator = controler.controler_translator:main',
#             'controler_rc = controler.controler_dumy_rc:main',
#             'controler_simulation = controler.controler_simulation:main',
#         ],
#     },
# )
from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'controler'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        
        
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='lemonx',
    maintainer_email='dudzinski.patryk.02@gmail.com',
    description='TODO: Package description',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [

            'controler_xyz = controler.controler_xyz:main',
            'controler_translator = controler.controler_translator:main',
            'controler_rc = controler.controler_dumy_rc:main',
            'controler_simulation = controler.controler_simulation:main',

        
            'joy_moveit = controler.joy_moveit:main',
            'joy_to_servo = controler.joy_to_servo_node:main',  
        ],
    },
)
