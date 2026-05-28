from setuptools import setup, find_packages

setup(
    name="autotest_runner",
    version="0.2.0",
    description="AutoTestRunner - 本地智能硬件自动化测试框架 (支持离线与云端双模)",
    author="AutoTestHub Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pytest>=7.0.0",
        "requests>=2.25.1",
        "pytest-html>=3.2.0",
        "PyYAML>=6.0"
    ],
    entry_points={
        "console_scripts": [
            "autotest-runner=autotest_runner.cli:main"
        ]
    },
)
