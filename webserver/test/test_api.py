import unittest

from webserver import create_app

class BasicTestCase(unittest.TestCase):
    def test_home(self):
        app = create_app(True)

        tester = app.test_client(self)
        response = tester.get('/api/games/1', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        print(response.data)

def run_tests():
    print('hello!!')
    unittest.main()