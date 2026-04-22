from setuptools import setup, find_packages

setup(
    name="girlfriend-agent",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.12",
    install_requires=[
        "fastapi>=0.136.0",
        "uvicorn>=0.44.0",
        "chromadb>=1.5.8",
        "sentence-transformers>=5.4.1",
        "numpy>=2.2.5",
        "pyyaml>=6.0.3",
        "pydantic>=2.0",
        "gitpython>=3.1",
        "httpx>=0.27",
    ],
    entry_points={
        "console_scripts": [
            "girlfriend-agent=src.engine_server:main",
        ],
    },
)
