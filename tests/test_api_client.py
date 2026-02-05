import unittest
from api_client import APIClient


class TestAPIClient(unittest.TestCase):
    def setUp(self):
        self.valid_credentials = {'username': 'valid_user', 'password': 'valid_pass'}
        self.invalid_credentials = {'username': 'invalid_user', 'password': 'invalid_pass'}

    def test_auth_headers(self):
        client = APIClient(self.valid_credentials)
        headers = client.session.headers
        # Per official spec: plaintext password, agent format, instance MD5
        self.assertIn('gamexAPIPassword', headers)
        self.assertIn('gamexAPIAgent', headers)
        self.assertIn('gamexAPIAgentInstance', headers)
        # Verify agent format: email.AppName.Version
        self.assertTrue('.BaccaratBot.' in headers['gamexAPIAgent'])
        # Verify instance is 32-char hex
        self.assertEqual(len(headers['gamexAPIAgentInstance']), 32)

    def test_invalid_auth(self):
        # This test expects the API to reject invalid credentials or channel
        client = APIClient(self.invalid_credentials)
        try:
            client.get_snapshot('dummy_channel')
        except Exception as e:
            # Accept 401, 403, 412, or Unauthorized as valid auth/channel errors
            self.assertTrue(
                any(code in str(e) for code in ['401', '403', '412']) or 'Unauthorized' in str(e)
            )
        else:
            self.fail('Expected authentication error')


if __name__ == "__main__":
    unittest.main()
