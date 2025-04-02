from setuptools import setup, find_packages

setup(
    name="athena",
    version="0.1.0",
    description="Knowledge Graph Engine for Tekton",
    author="Tekton Team",
    author_email="example@example.com",
    packages=find_packages(),
    install_requires=[
        "neo4j>=4.4.0",
        "py2neo>=2021.2.3",
        "fastapi>=0.68.0",
        "pydantic>=1.9.0",
        "sqlalchemy>=1.4.0",
        "pandas>=1.3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.12.0",
            "black>=21.5b2",
            "flake8>=3.9.0",
            "mypy>=0.812",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.9",
)