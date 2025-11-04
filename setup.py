#!/usr/bin/env python3
"""
heybud v1 — Your friendly CLI assistant with multi-provider LLM support
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="heybud",
    version="1.0.0",
    author="Rajat Vishwa",
    description="AI-powered CLI assistant with multi-provider LLM support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Rajat-Vishwa/heybud",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "openai>=1.0.0",
        "anthropic>=0.7.0",
        "google-generativeai>=0.3.0",
        "requests>=2.31.0",
        "pydantic>=2.0.0",
        "rich>=13.0.0",
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
        "pyperclip>=1.8.0",
        "pyyaml>=6.0",
        "httpx>=0.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "heybud-cli=cli.heybud_cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "cli": ["shell_wrapper_templates/*.sh"],
        "core": ["prompt_templates/*.yaml"],
    },
)
