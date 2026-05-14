from setuptools import find_packages, setup
from glob import glob
import os

package_name = "conveyor_sim"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "worlds"), glob("worlds/*.wbt")),
        (
            os.path.join("share", package_name, "controllers", "conveyor_controller"),
            glob("controllers/conveyor_controller/*"),
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="darhf",
    maintainer_email="didier.hernandez1972@gmail.com",
    description="Simulación Webots tipo digital twin para conveyor",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [],
    },
)
