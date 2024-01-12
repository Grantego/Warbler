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


class UserViewTestCase(TestCase):
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

    def test_users_show(self):
        """does the user page populate correctly?"""
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
        
            resp = c.get("/users/1234")

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<h4 id="sidebar-username">@testuser', str(resp.data))

    def test_show_following(self):
        """tests that any logged in user can view any other user following pages"""

        u = User.signup(username="new-user",
            email="testtest@test.com",
            password="password",
            image_url=None)
        u.id = 9876
        u.following.append(self.testuser)

        db.session.add(u)
        db.session.commit()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get('/users/9876/following')
            self.assertEqual(resp.status_code, 200)
            self.assertIn("<p>@testuser</p>", str(resp.data))

    def test_show_following_unauthorized(self):
        """tests that followers pages cannot be viewed by a logged-out user"""
        with self.client as c:
            resp = c.get('/users/1234/following', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))


    def test_show_followers(self):
        """tests that any logged in user can view any other user following pages"""

        u = User.signup(username="new-user",
            email="testtest@test.com",
            password="password",
            image_url=None)
        u.id = 9876
        u.followers.append(self.testuser)

        db.session.add(u)
        db.session.commit()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get('/users/9876/followers')
            self.assertEqual(resp.status_code, 200)
            self.assertIn("<p>@testuser</p>", str(resp.data))

    def test_show_followers_unauthorized(self):
        """tests that followers pages cannot be viewed by a logged-out user"""
        with self.client as c:
            resp = c.get('/users/1234/followers', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))


    def test_add_follow(self):
        """tests that follows are successfully added"""
        u = User.signup(username="new-user",
            email="testtest@test.com",
            password="password",
            image_url=None)
        u.id = 9876

        db.session.add(u)
        db.session.commit()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post('/users/follow/9876', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p>@new-user</p>', str(resp.data))

    
    def test_logged_out_add_follow(self):
        """tests that follows are not possible for a logged out user"""
        u = User.signup(username="new-user",
            email="testtest@test.com",
            password="password",
            image_url=None)
        u.id = 9876

        db.session.add(u)
        db.session.commit()
        with self.client as c:       
            resp = c.post('/users/follow/9876', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))           
            
    def test_toggle_like(self):
        """tests that user can like and unlike (also tests show_liked_messages through redirect)"""
        u = User.signup(username="new-user",
            email="testtest@test.com",
            password="password",
            image_url=None)
        u.id = 9876

        msg = Message(id=123, text='test message', user_id=u.id)

        db.session.add_all([u, msg])
        db.session.commit()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post('/users/add_like/123', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(self.testuser.likes), 1)
            self.assertIn('<a href="/users/9876">@new-user</a>', str(resp.data))

            resp2 = c.post('/users/add_like/123', follow_redirects=True)
            self.assertEqual(resp2.status_code, 200)
            self.assertEqual(len(self.testuser.likes), 0)
            self.assertNotIn('<a href="/users/9876">@new-user</a>', str(resp2.data))


    def test_unauthorized_toggle_like(self):
        """test that likes not available"""
        u = User.signup(username="new-user",
            email="testtest@test.com",
            password="password",
            image_url=None)
        u.id = 9876

        msg = Message(id=123, text='test message', user_id=u.id)

        db.session.add_all([u, msg])
        db.session.commit()

        with self.client as c:
            resp = c.post('/users/add_like/123', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))


    def test_stop_following(self):
        """tests that stop-following route correctly removes a user from a follow"""
        u = User.signup(username="new-user",
            email="testtest@test.com",
            password="password",
            image_url=None)
        u.id = 9876
        u.following.append(self.testuser)

        db.session.add(u)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = 9876
            
            resp = c.post('/users/stop-following/1234', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('testuser', str(resp.data))

    def test_unauth_stop_following(self):
        """tests that user must be logged in to stop following"""
        u = User.signup(username="new-user",
            email="testtest@test.com",
            password="password",
            image_url=None)
        u.id = 9876
        u.following.append(self.testuser)

        db.session.add(u)
        db.session.commit()

        with self.client as c:       
            resp = c.post('/users/follow/9876', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))


    def test_profile(self):
        """tests that profile page """      
        

