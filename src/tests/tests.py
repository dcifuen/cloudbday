#!/usr/bin/python
# encoding: utf-8
"""
tests.py
"""
import unittest
import base64

from google.appengine.ext import testbed, deferred, ndb
from birthday.models import User, get_birthdays

USAGE = """
Path to your sdk must be the first argument. To run type:

$ utrunner.py tests.py path/to/your/appengine/installation

Remember to set environment variable FLASK_CONF to TEST.
Loading configuration depending on the value of
environment variable allows you to add your own
testing configuration in src/birthday/settings.py

"""


class AppEngineFlaskTestCase(unittest.TestCase):

    def setUp(self):
        # Flask apps testing. See: http://flask.pocoo.org/docs/testing/
        from birthday import app
        self.app = app.test_client()
        app.config['TESTING'] = True
        app.config['CSRF_ENABLED'] = False
        self._ctx = app.test_request_context()
        self._ctx.push()

        # Setups app engine test bed. See: http://code.google.com/appengine/docs/python/tools/localunittesting.html#Introducing_the_Python_Testing_Utilities
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_user_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub(root_path=".")
        self.task_stub = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)

    def tearDown(self):
        self.testbed.deactivate()
        if getattr(self, '_ctx') and self._ctx is not None:
            self._ctx.pop()
        del self._ctx

    def run_queue_tasks(self, queue='default'):
        api_tasks = self.task_stub.GetTasks(queue)
        while len(api_tasks) >0:
            self.task_stub.FlushQueue(queue)
            for api_task in api_tasks:
                deferred.run(base64.b64decode(api_task['body']))
            api_tasks = self.task_stub.GetTasks(queue)

    def set_current_user(self, email, user_id, is_admin=False):
        self.testbed.setup_env(
            USER_EMAIL=email or '',
            USER_ID=user_id or '',
            USER_IS_ADMIN='1' if is_admin else '0'
        )


class UserTestCase(AppEngineFlaskTestCase):

    def test_get_birthdays(self):
        self.assertListEqual(
            [],
            get_birthdays(month=3, day=12),
            'Datastore empty, no birthdays'
        )
        user1_key = User(email='user@example.net', birth_day=12,
                         birth_month=3, receive_mail=True).put()
        user2_key = User(email='other@example.co', birth_day=10,
                         birth_month=6, receive_mail=True).put()
        self.assertListEqual(
            [user1_key.get()],
            get_birthdays(month=3, day=12),
            'List should have only one match'
        )
        ndb.delete_multi([user1_key, user2_key])

    def test_add_many_birthdays(self):
        User.add_many_birthdays([])
        self.assertListEqual([], User.query().fetch(),
                             'List empty. No users added')
        User.add_many_birthdays([
            {
                'email': 'david@eforcers.com',
                'birthday': '1985-03-01'
            },
            {
                'email': 'pedro@eforcers.com',
                'birthday': '--02-02'
            },
            {
                'email': 'juan@eforcers.com',
                'birthday': '09-05'
            },
            {
                'email': 'invalid@eforcers.com',
                'birthday': 'blablabla'
            }
        ])

        #Check users where created and dates are stored OK
        user1 = User.query(User.email == 'david@eforcers.com').get()
        self.assertEqual(user1.birth_year, 1985, 'Year not the same')
        self.assertEqual(user1.birth_month, 3, 'Month not the same')
        self.assertEqual(user1.birth_day, 1, 'Day not the same')

        user2 = User.query(User.email == 'pedro@eforcers.com').get()
        self.assertIsNone(user2.birth_year, 'Year not set')
        self.assertEqual(user2.birth_month, 2, 'Month not the same')
        self.assertEqual(user2.birth_day, 2, 'Day not the same')


        user3 = User.query(User.email == 'juan@eforcers.com').get()
        self.assertIsNone(user3.birth_year, 'Year not set')
        self.assertEqual(user3.birth_month, 9, 'Month not the same')
        self.assertEqual(user3.birth_day, 5, 'Day not the same')

        #Check user was not created
        self.assertIsNone(
            User.query(User.email == 'invalid@eforcers,com').get(),
            'Invalid user was not supposed to be created'
        )
        #Clean yourself
        ndb.delete_multi([user1.key, user2.key, user3.key])

    def test_get_all_birthdays(self):
        self.assertListEqual([], User.get_all_birthdays(),
                             'List empty. No users added')
        user1_key = User(email='david@eforcers.com', birth_year=1985,
                         birth_month=3, birth_day=1).put()

        user2_key = User(email='pedro@eforcers.com', birth_month=2,
                         birth_day=2).put()

        user3_key = User(email='juan@eforcers.com', birth_month=9,
                         birth_day=5).put()
        self.assertEqual(3, len(User.get_all_birthdays()), 'Length is not '
                                                           'right')
        #Clean yourself
        ndb.delete_multi([user1_key, user2_key, user3_key])

        
class DemoTestCase(AppEngineFlaskTestCase):

    def test_home_redirects(self):
        rv = self.app.get('/')
        assert rv.status == '302 FOUND'    

    def test_says_hello(self):
        rv = self.app.get('/hello/world')
        assert 'Hello world' in rv.data

    def test_displays_no_data(self):
        rv = self.app.get('/examples')
        assert 'No examples yet' in rv.data

    def test_inserts_data(self):
        self.set_current_user(u'john@example.com', u'123')
        rv = self.app.post('/example/new', data=dict(
            example_name='An example',
            example_description='Description of an example'
        ), follow_redirects=True)
        assert 'Example successfully saved' in rv.data

        rv = self.app.get('/examples')
        assert 'No examples yet' not in rv.data
        assert 'An example' in rv.data
    
    def test_admin_login(self):
        #Anonymous
        rv = self.app.get('/admin_only')
        assert rv.status == '302 FOUND'
        #Normal user
        self.set_current_user(u'john@example.com', u'123')
        rv = self.app.get('/admin_only')
        assert rv.status == '302 FOUND'
        #Admin
        self.set_current_user(u'john@example.com', u'123', True)
        rv = self.app.get('/admin_only')
        assert rv.status == '200 OK'

    def test_404(self):
        rv = self.app.get('/missing')
        assert rv.status == '404 NOT FOUND'
        assert '<h1>Not found</h1>' in rv.data


if __name__ == '__main__':
    unittest.main()
