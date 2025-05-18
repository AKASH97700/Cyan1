import re
from setuptools import setup, find_packages

def get_version():
    with open("your_package/__init__.py", "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'^__version__\s*=\s*[\'"]([^\'"]+)[\'"]', content, re.M)
    if match:
        return match.group(1)
    raise RuntimeError("Unable to find __version__ string.")

setup(
    name="your-package",
    version=get_version(),
    author="Your Name",
    author_email="your.email@example.com",
    description="A short description of your package",
    packages=find_packages(),
    install_requires=[],
    python_requires=">=3.7",
)