"""Setup file for kp-registry package."""
from setuptools import setup

setup(
    name="kp-registry",
    version="3.0.0",
    author="CoVar",
    url="https://github.com/ranking-agent/kp_registry",
    description="Translator KP Registry",
    packages=["kp_registry"],
    include_package_data=True,
    zip_safe=False,
    license="MIT",
    python_requires=">=3.6",
    install_requires=[
        "httpx",
        "reasoner_pydantic",
    ],
)
