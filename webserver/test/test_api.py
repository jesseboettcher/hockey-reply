import unittest

from webserver import create_app

class BasicTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(True)
        cls.tester = cls.app.test_client(cls)

    @classmethod
    def tearDownClass(cls):
        del(cls.app)

    def test_get_all_games(self):
        response = self.tester.get('/api/games/1', content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_get_single_game(self):
        response = self.tester.get('/api/game/309536', content_type='application/json')
        self.assertEqual(response.status_code, 200)

        response = self.tester.get('/api/game/0', content_type='application/json')
        self.assertEqual(response.status_code, 400)
