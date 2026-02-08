import os
import setuptools

_version_info = {}
with open(os.path.join("AU2", "_version.py")) as f:
    exec(f.read(), _version_info)

with open("requirements.txt", "r") as requirements:
    reqs = requirements.read().splitlines()

setuptools.setup(
    name='Auto-Umpire 2',
    version=_version_info["__version__"],
    description="Software to run the Cambridge Assassins' Guild",
    author="B. M. Syiek, P. Jackson, and A. C. Newton",
    author_email="",
    packages=setuptools.find_packages(include=['AU2*']),
    include_package_data=True,
    install_requires=reqs,
    python_requires='>=3.9',
    entry_points={
        'console_scripts': [
            "au2 = AU2.frontends.inquirer_cli:main",
            "au2_packager = AU2.frontends.au2_packager:main"
        ],
    },
)
