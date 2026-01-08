import re
from flask_restx import Namespace, Resource, fields
from app.extensions import db
from app.models import User
from sqlalchemy.exc import IntegrityError

user_ns = Namespace('users', description='User operations')

# swagger model
user_input_model = user_ns.model('UserInput',{
    'username': fields.String(required=True),
    'email': fields.String(required=True),
    'password': fields.String(required=True)
})

user_output_model = user_ns.model('UserOutput', {
    'id': fields.Integer,
    'username': fields.String,
    'email': fields.String
})

def validate_email_format(email):
    if not email:
        return False
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

def validate_password_strength(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password): 
        return False
    if not re.search(r"[a-z]", password): 
        return False
    if not re.search(r"\d", password):    
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): 
        return False
    return True

# 1. Resource: Users
@user_ns.route('/users')
class UserList(Resource):
    # get: retrieves the entire user list
    @user_ns.marshal_list_with(user_output_model) # all user json list
    def get(self): 
        return User.query.all() # select*from users
    
    # post: creates new resource
    @user_ns.expect(user_input_model)
    @user_ns.marshal_with(user_output_model) # json 
    def post(self):
        data = user_ns.payload

        if not validate_email_format(data['email']):
            user_ns.abort(400, "Invalid email format.")
            
        if not validate_password_strength(data.get('password', '')):
            user_ns.abort(400, "Password is too weak. It must be at least 8 chars, contain uppercase, lowercase, number and special char.")

        user = User(username=data['username'], email=data['email'], password=data.get('password',''))
        
        try:
            db.session.add(user) # wait
            db.session.commit() # record
            return user, 201
        except IntegrityError:
            db.session.rollback() # cancel
            user_ns.abort(400, "This username or email address is registered.")

@user_ns.route('/users/<int:id>')
@user_ns.response(404,'user not found')
class UserResource(Resource):
    # get: retrieves the one user
    @user_ns.marshal_with(user_output_model)
    def get(self, id):
        return User.query.get_or_404(id) #select*from users where id
    
    #patch: updates the existing resource
    @user_ns.expect(user_input_model, validate=False)
    @user_ns.marshal_with(user_output_model)
    def patch(self, id): 
        user = User.query.get_or_404(id)
        data = user_ns.payload
        if 'username' in data: user.username = data['username']
        if 'email' in data: user.email = data['email']
        if 'password' in data: user.password = data['password']

        db.session.commit()
        return user
    
    #delete: deletes user based on id
    def delete(self, id):
        user = User.query.get_or_404(id)
        db.session.delete(user)
        db.session.commit()
        return '', 204
