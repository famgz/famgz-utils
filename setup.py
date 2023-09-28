from setuptools import setup, find_packages

with open('requirements.txt') as f:
    REQUIREMENTS = f.readlines()

setup(
    name='famgz_utils',
    version='0.1',
    license='MIT',
    author="famgz",
    author_email='famgz@proton.me',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    url='https://github.com/famgz/famgz_utils',
    install_requires=REQUIREMENTS
)
