"""Setup file for kp-registry package."""
from setuptools import setup

setup(
    name='kp_registry',
    version='2.4.2',
    author='CoVar',
    url='https://github.com/ranking-agent/kp_registry',
    description='Translator KP Registry',
    packages=['kp_registry', 'kp_registry.routers'],
    include_package_data=True,
    zip_safe=False,
    license='MIT',
    python_requires='>=3.6',
)
