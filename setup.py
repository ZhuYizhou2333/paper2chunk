from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="paper2chunk",
    version="0.1.0",
    author="ZhuYizhou",
    description="Convert PDF documents into RAG-friendly semantic chunks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ZhuYizhou2333/paper2chunk",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pypdf2>=3.0.0",
        "pymupdf>=1.23.0",
        "openai>=1.0.0",
        "anthropic>=0.7.0",
        "markdown>=3.4.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
        "pillow>=10.0.0",
        "numpy>=1.24.0",
    ],
    entry_points={
        "console_scripts": [
            "paper2chunk=paper2chunk.cli:main",
        ],
    },
)
