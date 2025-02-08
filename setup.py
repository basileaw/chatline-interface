from setuptools import setup, find_packages

setup(
    name="chatline",
    version="0.1.0",
    description="A chat interface implementation",
    packages=find_packages(),
    install_requires=[
        "boto3",
        "httpx",
        "rich",
        "prompt-toolkit",
    ],
    python_requires=">=3.12",
)
