from setuptools import setup, find_packages

setup(
    name="open-memory-capsule",
    version="0.1.0",
    description="Python SDK for Open Memory Capsule — capture everything, search naturally",
    long_description=open("../../README.md").read(),
    long_description_content_type="text/markdown",
    author="Open Memory Capsule Contributors",
    url="https://github.com/moizBhai97/memory_capsule",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=["httpx>=0.27.0"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
