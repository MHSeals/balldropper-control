from setuptools import find_packages, setup

package_name = 'ball_dropper_control'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='MHSeals',
    maintainer_email='todo@example.com',
    description='ROS 2 node for controlling the ball dropper mechanism.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'ball_dropper_control = ball_dropper_control.ball_dropper_control_node:main',
            'load_dropper = ball_dropper_control.load_dropper:main',
        ],
    },
)
