from setuptools import setup, find_packages


extras_require = dict(
    vault=[
        'mnemonic',
    ],
    test=[
        'django',
        'djangorestframework',
        'pytest',
        'pytest-cov',
        'pytest-django',
        'web3[dev]>=6.0.0b9',
    ],
    ethereum=[
        'web3>=6.0.0b9',  # no [dev] for persistent deployments
    ],
    tezos=[
        'pytezos>3.4',
    ],
    binary=[
        'pysodium',
        'secp256k1',
        'fastecdsa',
    ],
)

extras_require['all'] = []
for name, deps in extras_require.items():
    if name == 'binary':
        continue
    extras_require['all'] += deps


setup(
    name='djwebdapp',
    versioning='dev',
    setup_requires='setupmeta',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'django-model-utils',
        'djfernet>=0.8.1',
        'django-picklefield>=3.0.1',
        'pymich>=0.9.8',
    ],
    extras_require=extras_require,
    author='James Pic',
    author_email='jamespic@gmail.com',
    url='https://yourlabs.io/oss/djwebdapp',
    include_package_data=True,
    license='MIT',
    keywords='cli',
    python_requires='>=3.8',
)
