import setuptools

with open("README.md") as fp:
    long_description = fp.read()

CDK_VERSION="2.20.0"

setuptools.setup(
    name="drupal",
    version="1.1.0",

    description="AWS Marketplace Pattern for Drupal by Ordinary Experts.",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="Ordinary Experts",

    package_dir={"": "drupal"},
    packages=setuptools.find_packages(where="drupal"),

    install_requires=[
        f"aws-cdk-lib=={CDK_VERSION}",
        f"constructs>=10.0.0,<11.0.0",
        f"oe-patterns-cdk-common@git+https://github.com/ordinaryexperts/aws-marketplace-oe-patterns-cdk-common@3.1.0"
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: Apache Software License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
