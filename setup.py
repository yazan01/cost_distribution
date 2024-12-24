from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in cost_distribution/__init__.py
from cost_distribution import __version__ as version

setup(
	name="cost_distribution",
	version=version,
	description="Cost Distribution",
	author="Furqan Asghar",
	author_email="furqan.79000@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
