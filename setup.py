from setuptools import find_packages, setup

setup(
    name="tinaa-playwright-msp",
    version="0.1.0",
    description="TINAA - Testing Intelligence Network Automation Assistant MSP",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "pygls>=1.0.0",
        "pytest>=7.0.0",
        "pytest-playwright>=0.3.0",
        "fastmcp==2.8.0",
        "pydantic>=2.0.0"
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
)
