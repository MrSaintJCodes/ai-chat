class BaseConnector:
    provider = None

    def test_connection(self):
        raise NotImplementedError