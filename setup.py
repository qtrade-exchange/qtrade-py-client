from distutils.core import setup

setup(
    name='qtrade_client',
    install_requires=[
        'click',
        'requests'
    ],
    version='0.1',
    packages=['qtrade_client', 'qtrade_client.cli'],
    python_requires='>=2.7.0',
    entry_points={
        'console_scripts': ['qtapi = qtrade.cli:entry'],
    },
)
