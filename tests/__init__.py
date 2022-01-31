from json import load

from routerling.utils import preprocessor


with open('tests/asgi.json') as mocked:
    mock_scope = load(mocked)
    mock_metadata = preprocessor(mock_scope)
    mocked.close()
mock_body = {'body': "{'flat': True, 'age': 35, 'title': 'Engineering Manager'}"}
mock_receive = {}
