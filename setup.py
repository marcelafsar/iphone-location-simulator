"""
Setup script for Marcel Location Simulator
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="iphone-location-simulator",
    version="1.0.0",
    author="Marcel Afsar",
    author_email="marcel.afsar@icloud.com",
    description="Premium iPhone GPS Location Simulator for Windows, macOS, and Linux",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.9",
    install_requires=[
        "pymobiledevice3>=3.0.0",
        "click>=8.0.0",
        "pyyaml>=6.0",
        "PyQt6>=6.5.0",
        "PyQt6-WebEngine>=6.5.0",
        "gpxpy>=1.5.0",
        "sqlalchemy>=2.0.0",
        "loguru>=0.7.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-qt>=4.2.0",
            "pyinstaller>=5.13.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "iphone-location-simulator=src.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.json", "*.html", "*.qss"],
    },
)