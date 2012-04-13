"""
Test for birthday app
To run tests: "manage.py test birthday".

"""

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User


class CoursesViewTestCase(TestCase):
    def setUp(self):
        """
        Create and login with test user. The view requires to be logged in
        
        """
        User.objects.create_user('john', 'test@domain.com', 'johnpassword')
        self.client.login(username='john', password='johnpassword')
        
    def test_list(self):
        """
        Tests the course list displayed in the administration panel
        
        """
        url = reverse('course_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
