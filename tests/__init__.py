from json import load

from routerling.utils import preprocessor


with open("tests/asgi.json") as mocked:
    mock_scope = load(mocked)
    mock_metadata = preprocessor(mock_scope)
    mocked.close()

sample_body = {
    'type': 'http.request.body',
    'body': b'{"example": "Some JSON data"}',
    'more_body': False
}

mock_body = {"body": b"{'flat': True, 'age': 35, 'title': 'Engineering Manager'}"}
mock_receive = {}
