from setuptools import setup, find_packages

with open('requirements.txt') as f:
    REQUIREMENTS = f.readlines()

setup(
    name='famgz_utils',
    version='0.1',
    license='MIT',
    author="famgz",
    author_email='famgz@proton.me',
    packages=['famgz_utils'],
    package_dir={'famgz_utils': 'src/famgz_utils'},
    package_data={'famgz_utils': ['mouse_movements/*.json']},
    include_package_data=True,
    url='https://github.com/famgz/famgz_utils',
    install_requires=REQUIREMENTS
)
