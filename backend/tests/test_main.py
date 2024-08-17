import pytest
import requests_mock


def test_upload_file():
    requests_mock.post('http://localhost:8080/file', data= {'name': 'awesome-mock'})