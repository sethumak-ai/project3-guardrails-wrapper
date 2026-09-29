from setuptools import setup, find_packages

setup(
    name="guardrails-wrapper",
    version="0.1.0",
    description="Output filtering, structural enforcement, and rate limiting wrapped around ZenAssist",
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.9",
    install_requires=[
        "injectguard @ git+https://github.com/sethumak-ai/injectguard.git",
        "requests>=2.31.0",
    ],
    extras_require={
        "streamlit": ["streamlit>=1.35.0"],
        "dev": ["pytest>=8.0.0"],
    },
)
