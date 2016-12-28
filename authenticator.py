from flask import request, Response
from functools import wraps

class authenticator:
    def __init__(self, credentials):
        self.validCredentials = credentials

    def check_auth(self, username, password):
        """This function is called to check if a username /
        password combination is valid.
        """
        for c in self.validCredentials:
            if c['username'] == username and c['password'] == password:
                return True
        return False

    def authenticate(self):
        """Sends a 401 response that enables basic auth"""
        return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Test Realm"'})

    def passwordError(self):
        """Sends a 401 response"""
        return Response(
        'Error, password need to be set!', 401,
        {'WWW-Authenticate': 'Basic realm="Test Realm"'})

    def requires_auth(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not auth or not self.check_auth(auth.username, auth.password):
                return self.authenticate()
            return f(*args, **kwargs)
        return decorated
