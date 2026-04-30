"""
Pytest configuration and shared fixtures for Drupal integration tests.
"""

import os
from pathlib import Path

import boto3
import pytest
import yaml


def pytest_addoption(parser):
    parser.addoption("--base-url", action="store", default=None,
                     help="Base URL for the application under test")
    parser.addoption("--stack-name", action="store", default=None,
                     help="CloudFormation stack name")
    parser.addoption("--skip-ui", action="store_true", default=False,
                     help="Skip UI/browser tests")


@pytest.fixture(scope="session")
def config():
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def base_url(request, config):
    url = (
        request.config.getoption("--base-url")
        or os.environ.get("TEST_BASE_URL")
        or config["urls"]["base_url"]
    )
    return url.rstrip("/")


@pytest.fixture(scope="session")
def stack_name(request, config):
    return (
        request.config.getoption("--stack-name")
        or os.environ.get("TEST_STACK_NAME")
        or config["aws"]["stack_name"]
    )


@pytest.fixture(scope="session")
def aws_region(config):
    return os.environ.get("AWS_REGION") or config["aws"]["region"]


@pytest.fixture(scope="session")
def cloudformation_client(aws_region):
    return boto3.client("cloudformation", region_name=aws_region)


@pytest.fixture(scope="session")
def stack_outputs(cloudformation_client, stack_name):
    response = cloudformation_client.describe_stacks(StackName=stack_name)
    stack = response["Stacks"][0]
    return {o["OutputKey"]: o["OutputValue"] for o in stack.get("Outputs", [])}


def pytest_collection_modifyitems(config, items):
    if config.getoption("--skip-ui"):
        skip_ui = pytest.mark.skip(reason="--skip-ui option provided")
        for item in items:
            if "ui" in item.keywords:
                item.add_marker(skip_ui)
