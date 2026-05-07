"""Package setup for cronjot."""

from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="cronjot",
    version="0.1.0",
    author="cronjot contributors",
    description="Lightweight cron job logger with digest summaries via email or Slack",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/cronjot",
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.28",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov",
        ],
    },
    entry_points={
        "console_scripts": [
            "cronjot=cronjot.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: System :: Logging",
        "Topic :: Utilities",
    ],
)
