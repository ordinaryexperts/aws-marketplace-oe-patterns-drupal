"""
Health and basic connectivity tests for Drupal.
Run after `make deploy` to verify the dev stack is reachable and responding.
"""

import pytest
import requests


class TestDrupalHealth:
    """Infrastructure and basic application health."""

    def test_https_accessible(self, base_url):
        response = requests.get(base_url, timeout=30, allow_redirects=True)
        assert response.status_code == 200, \
            f"Failed to reach {base_url}: status {response.status_code}"
        assert response.url.startswith("https://"), \
            "Site should redirect to HTTPS"

    def test_serves_html(self, base_url):
        response = requests.get(base_url, timeout=30, allow_redirects=True)
        ctype = response.headers.get("Content-Type", "")
        assert "text/html" in ctype, \
            f"Expected HTML content-type, got: {ctype}"

    def test_drupal_x_generator_header(self, base_url, config):
        """Drupal sets X-Generator: Drupal <major> (https://www.drupal.org)."""
        response = requests.get(base_url, timeout=30, allow_redirects=True)
        gen = response.headers.get("X-Generator", "")
        if not gen:
            pytest.skip("X-Generator header not set (may be stripped by CDN)")
        expected_major = config["application"]["expected_version_major"]
        assert f"Drupal {expected_major}" in gen, \
            f"Expected 'Drupal {expected_major}' in X-Generator, got: {gen}"
