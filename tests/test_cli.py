from unittest.mock import MagicMock, patch

import requests

import cli


def fake(status, body):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = body
    return m


@patch("cli.requests.request")
def test_list(mock_req, capsys):
    mock_req.return_value = fake(200, [{"id": 1}])
    assert cli.main(["list"]) == 0
    assert '"id": 1' in capsys.readouterr().out


@patch("cli.requests.request")
def test_add(mock_req):
    mock_req.return_value = fake(201, {"id": 4})
    assert cli.main(["add", "--name", "Tea", "--price", "2", "--stock", "5"]) == 0
    assert mock_req.call_args[0][0] == "POST"


@patch("cli.requests.request")
def test_update_requires_field(mock_req, capsys):
    assert cli.main(["update", "1"]) == 1
    mock_req.assert_not_called()


@patch("cli.requests.request")
def test_api_error(mock_req, capsys):
    mock_req.return_value = fake(404, {"error": "Item not found"})
    assert cli.main(["view", "99"]) == 1
    assert "Item not found" in capsys.readouterr().out


@patch("cli.requests.request")
def test_connection_error(mock_req, capsys):
    mock_req.side_effect = requests.ConnectionError()
    assert cli.main(["delete", "1"]) == 1
    assert "cannot reach" in capsys.readouterr().out


def test_find_requires_arg(capsys):
    assert cli.main(["find"]) == 1