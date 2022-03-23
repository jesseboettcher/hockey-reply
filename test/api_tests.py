import unittest

from ..webserver import create_app

class BasicTestCase(unittest.TestCase):
    def test_home(self):
        app = create_app()

        tester = app.test_client(self)
        response = tester.get('/api/games/1', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        print(response.data)

if __name__ == '__main__':
    unittest.main()