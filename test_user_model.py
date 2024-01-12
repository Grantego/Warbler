"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User, Message, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""
        db.drop_all()
        db.create_all()

        u1 = User.signup("test1", "email1@email.com", "password", None)
        uid1 = 1111
        u1.id = uid1

        u2 = User.signup("test2", "email2@email.com", "password", None)
        uid2 = 2222
        u2.id = uid2

        db.session.commit()

        u1 = User.query.get(uid1)
        u2 = User.query.get(uid2)

        self.u1 = u1
        self.uid1 = uid1

        self.u2 = u2
        self.uid2 = uid2

        self.client = app.test_client()

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res


    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

    def test_user_follows(self):
        """Does following a user correctly ?"""
        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertEqual(len(self.u2.followers), 1)
        self.assertEqual(len(self.u2.following), 0)
        self.assertEqual(len(self.u1.following), 1)
        self.assertEqual(len(self.u1.followers), 0)

        self.assertEqual(self.u2.followers[0].id, self.u1.id)
        self.assertEqual(self.u1.following[0].id, self.u2.id)

    def test_is_following(self):
        """Does is_following successfully detect when user1 is not following user2?"""
        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertTrue(self.u1.is_following(self.u2))
        self.assertFalse(self.u2.is_following(self.u1))

    def test_signup(self):
        """Does sign-up successfully make a new user with a hashed pass?"""
        new_user = User.signup('test3', 'test3@test.com', 'password', None)
        uid = 9999
        new_user.id= uid
        db.session.commit()

        new_user = User.query.get(uid)
        self.assertIsNotNone(new_user)
        self.assertEqual(new_user.username, 'test3')
        self.assertEqual(new_user.email, 'test3@test.com')
        self.assertNotEqual(new_user.password, 'password')
        self.assertTrue(new_user.password.startswith('$2b$'))

    def test_invalid_username_signup(self):
        """tests if a username is already taken returns an error."""
        invalid= User.signup(None, 'test@test.com', 'password', None)
        uid = 9999
        invalid.id = uid
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()


    def test_invalid_password_signup(self):
        """tests if a username is already taken returns an error."""
        with self.assertRaises(ValueError) as context:
            User.signup('testtest', 'email@email.com', '', None)

        with self.assertRaises(ValueError) as context:
            User.signup('testtest', 'email@email.com', None, None)


    def test_invalid_email_signup(self):
        """tests if a username is already taken returns an error."""
        invalid = User.signup("testtest", None, "password", None)
        uid = 9999
        invalid.id = uid
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()


    def test_authenticate(self):
        """Tests that authenticate properly returns a user on valid login"""
        u = User.authenticate(self.u1.username, 'password')
        self.assertIsNotNone(u)
        self.assertEqual(u.id, self.uid1)

    
    def test_invalid_username(self):
        """Tests that authentication returns false on invalid username"""
        self.assertFalse(User.authenticate("invaliduser", "password"))


    def test_invalid_password(self):
        """Tests that authentication returns false on invalid password"""
        self.assertFalse(User.authenticate(self.u1.username, "badpassword"))