from setuptools import setup, find_packages


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
    extras_require=dict(
        vault=[
            'cryptography',
        ],
        tezos=[
            'pytezos',
        ],
        test=[
            'django',
            'djangorestframework',
            'freezegun',
            'httpx',
            'pytest',
            'pytest-cov',
            'pytest-django',
            'pytest-asyncio',
        ],
    ),
    author='James Pic',
    author_email='jamespic@gmail.com',
    url='https://yourlabs.io/oss/cli2',
    include_package_data=True,
    license='MIT',
    keywords='cli',
    python_requires='>=3.8',
)
