def assert_headers(received_headers: dict, expected_headers: dict) -> None:
    received = {key.lower(): val for key, val in received_headers.items()}
    expected = {key.lower(): val for key, val in expected_headers.items()}
    for key, value in expected.items():
        assert key in received
        assert received[key] == value
