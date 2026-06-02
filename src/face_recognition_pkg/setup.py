from setuptools import find_packages, setup

package_name = 'face_recognition_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='darhf',
    maintainer_email='didier.hernandez1972@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
		'face_recognition_node = face_recognition_pkg.face_recognition_node:main',
		'register_faces_offline = face_recognition_pkg.register_faces_offline:main',
		'preprocess_faces = face_recognition_pkg.preprocess_faces:main',
		'face_auth_node = face_recognition_pkg.face_auth_node:main',
        ],
    },
)
