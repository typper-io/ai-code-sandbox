from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ai-code-sandbox",
    version="0.1.0",
    author="João Barros",
    author_email="augustoj311@gmail.com",
    description="A secure sandbox for running AI-generated code",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/typper-io/ai-code-sandbox",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.7",
    install_requires=[
        "docker",
    ],
)