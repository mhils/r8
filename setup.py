#!/usr/bin/env python3
import re
from pathlib import Path

from setuptools import find_packages, setup

here = Path(__file__).parent

VERSION = re.search(
    r'__version__ = "(.+?)"',
    (here / "r8" / "__init__.py").read_text()
).group(1)

long_description = (here / "README.md").read_text()

setup(
    name="r8",
    version=VERSION,
    description="A ctf-style autograding system.",
    long_description=long_description,
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Education",
        "Operating System :: OS Independent",
        "Topic :: Education",
        "Topic :: Education :: Computer Aided Instruction (CAI)",
        'Programming Language :: Python :: 3.9',
    ],
    keywords="ctf grading capture the flag networking",
    url="https://github.com/mhils/r8",
    author="Maximilian Hils",
    autor_email="pypi@maximilianhils.com",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "r8 = r8.cli:main",
        ],
        "r8.challenges": [
            "dir = r8.builtin_challenges"
        ]
    },
    install_requires=[
        "click",
        "texttable",
        "argon2_cffi",
        "aiohttp",
        "aiohttp_jinja2",
        "itsdangerous",
        "blinker",
    ],
    extras_require={
        "faster": [
            "aiohttp[speedups]",
        ],
        "dev": [
            "sphinx",
            "sphinxcontrib-trio",
            "pytest",
        ]
    }
)
