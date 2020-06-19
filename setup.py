"""Setup file for kp-registry package."""
from setuptools import setup

setup(
    name='kp_registry',
    version='0.1.0-dev0',
    author='Patrick Wang',
    author_email='patrick@covar.com',
    url='https://github.com/TranslatorIIPrototypes/kp_registry',
    description='Translator KP Registry',
    packages=['kp_registry', 'kp_registry.routers'],
    include_package_data=True,
    zip_safe=False,
    license='MIT',
    python_requires='>=3.6',
)
