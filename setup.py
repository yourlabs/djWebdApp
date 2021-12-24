from setuptools import setup, find_packages


extras_require = dict(
    vault=[
        'django-fernet-fields',
        'mnemonic',
    ],
    tezos=[
        'pytezos',
    ],
    test=[
        'django',
        'djangorestframework',
        'pytest',
        'pytest-cov',
        'pytest-django',
    ],
)

extras_require['all'] = []
for deps in extras_require.values():
    extras_require['all'] += deps


setup(
    name='djwebdapp',
    versioning='dev',
    setup_requires='setupmeta',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'django-model-utils',
        'tenacity',
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
