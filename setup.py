from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="universal-api",
    version="0.1.0",
    author="Tony A. Ginart",
    author_email="tginart@gmail.com",
    description="A simple universal API simulator using language models",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/universal-api",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "litellm",
        "fastapi",
        "uvicorn",
        "pydantic",
        "httpx",
    ],
    entry_points={
        "console_scripts": [
            "universal-api-server=universal_api.cli:main",
        ],
    },
) 