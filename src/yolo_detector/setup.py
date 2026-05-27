from setuptools import find_packages, setup
from glob import glob
import os

package_name = "yolo_detector"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "models"), glob("models/*.pt")),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="darhf",
    maintainer_email="didier.hernandez1972@gmail.com",
    description="YOLO object detector for ROS2 Jazzy using /camera/image_raw",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "yolo_detector_node = yolo_detector.yolo_detector_node:main",
        ],
    },
)
