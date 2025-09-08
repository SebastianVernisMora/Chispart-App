#!/usr/bin/env python3
"""
Setup script para Blackbox Hybrid Tool
"""

from setuptools import setup, find_packages
from pathlib import Path

# Leer README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="blackbox-hybrid-tool",
    version="0.1.0",
    author="Blackbox AI",
    author_email="info@blackbox.ai",
    description="Herramienta híbrida de testing y análisis de código con IA",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/blackboxai/blackbox-hybrid-tool",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Quality Assurance",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "click>=8.0.0",
        "rich>=12.0.0",
        "python-dotenv>=0.19.0",
        "google-generativeai>=0.3.0",
        "openai>=1.0.0",
        "anthropic>=0.7.0",
    ],
    extras_require={
        "dev": [
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
            "pre-commit>=2.17.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "blackbox-tool=blackbox_hybrid_tool.cli.main:main",
            "blackbox-hybrid-tool=blackbox_hybrid_tool.cli.main:main",
            "blackbox_hybrid_tool=blackbox_hybrid_tool.cli.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
