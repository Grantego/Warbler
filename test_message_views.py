"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)
        
        self.testuser_id = 1234
        self.testuser.id = self.testuser_id

        db.session.commit()

    def test_add_message(self):
        """Can use add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"}, follow_redirects=True)

            # Make sure it redirects
            self.assertEqual(resp.status_code, 200)

            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")

    def test_add_no_session(self):
        """Does the page prevent new messsages from being posted if not logged in?"""
        with self.client as c:
            resp = c.post('/messages/new', data={'text': 'Hello'}, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

    def test_add_invalid_user(self):
        """test if if adding message works with an invalid session ID"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = 99999

        resp = c.post("/messages/new", data={'text': 'Hello'}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Access unauthorized", str(resp.data))


    def test_messages_show(self):
        """tests that message page loads properly"""
        msg = Message(id=123, text='test message', user_id=self.testuser_id)

        db.session.add(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            m = Message.query.get(123)

            resp = c.get(f'/messages/{m.id}')

            self.assertEqual(resp.status_code, 200)
            self.assertIn(m.text, str(resp.data))

    
    def test_invalid_messages_show(self):
            """test 404 returned for invalid messages"""
            with self.client as c:
                with c.session_transaction() as sess:
                    sess[CURR_USER_KEY] = self.testuser.id  

            resp = c.get('/messages/9999')
            self.assertEqual(resp.status_code, 404)

        
    def test_message_destroy(self):
        """test that messages are deleted"""
        with self.client as c:
            with c.session_transaction() as sess:
               sess[CURR_USER_KEY] = self.testuser.id

            msg = Message(id=123, text='test text', user_id=self.testuser.id)
            db.session.add(msg)
            db.session.commit()

            m = Message.query.get(123)
            self.assertEqual(len(self.testuser.messages), 1)

            resp = c.post(f'/messages/{m.id}/delete', follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(self.testuser.messages), 0)


    def test_unauthorized_message_destroy(self):
            """tests that messages can only be deleted by the logged in user"""
            
            u = User.signup(username="unauthorized-user",
                email="testtest@test.com",
                password="password",
                image_url=None)
            u.id = 9876
            
            msg = Message(id=123, text='a test message', user_id = self.testuser_id)

            db.session.add_all([u, msg])
            db.session.commit()

            with self.client as c:
                with c.session_transaction() as sess:
                    sess[CURR_USER_KEY] = 9876

                resp = c.post('/messages/123/delete', follow_redirects=True)
                self.assertEqual(resp.status_code, 200)
                self.assertIn("Access unauthorized", str(resp.data))
    
    def test_message_destroy_no_login(self):
        """Tests that messages cannot be deleted by someone not logged in"""
        msg = Message(id=123, text='a test message', user_id = self.testuser_id)
        db.session.add(msg)
        db.session.commit()

        with self.client as c:
            resp = c.post('/messages/123/delete', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

            msg = Message.query.get(123)
            self.assertIsNotNone(msg)