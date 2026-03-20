from django.test import TestCase


class HelloWorldViewTest(TestCase):
    def test_index_returns_200(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_index_contains_greeting(self):
        response = self.client.get('/')
        self.assertContains(response, 'おはようございます')

    def test_index_contains_morning_alarm_message(self):
        response = self.client.get('/')
        self.assertContains(response, '朝8時になりました。朝礼お願いします')

    def test_index_contains_evening_alarm_message(self):
        response = self.client.get('/')
        self.assertContains(response, '明日もよろしくお願いします')

    def test_index_contains_alarm_controls(self):
        response = self.client.get('/')
        self.assertContains(response, 'アラーム設定')
        self.assertContains(response, 'アラームを開始')
