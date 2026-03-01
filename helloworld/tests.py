from django.test import TestCase


class HelloWorldViewTest(TestCase):
    def test_index_returns_200(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_index_contains_greeting(self):
        response = self.client.get('/')
        self.assertContains(response, 'おはようございます')
