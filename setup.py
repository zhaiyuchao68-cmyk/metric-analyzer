from setuptools import setup, find_packages

setup(
    name="metric-analyzer",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "streamlit>=1.30.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "plotly>=5.18.0",
        "openpyxl>=3.1.0",
        "pyyaml>=6.0",
    ],
)
