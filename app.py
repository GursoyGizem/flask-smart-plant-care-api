import os
import numpy as np
import pandas as pd
import tensorflow as tf
import joblib

from flask import Flask
from flask_restx import Api, Resource, fields
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from PIL import Image
from extensions import db
from sqlalchemy.exc import IntegrityError
from models import User, Plant, GrowthLog, DiseaseCheck, PlantCare, DiseaseType

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# model load
growth_model = None
disease_model = None
model_columns = []

try:
    if os.path.exists("tabular_data/plant_growth.pkl"):
        growth_model = joblib.load("tabular_data/plant_growth.pkl")
        print("Plant growth model loaded.")
        
        csv_path = os.path.join("tabular_data", "plant_growth_data.csv")
        if os.path.exists(csv_path):
            df_ref = pd.read_csv(csv_path)
            if 'Growth_Milestone' in df_ref.columns:
                df_ref = df_ref.drop(columns=['Growth_Milestone'])
            df_encoded_ref = pd.get_dummies(df_ref, columns=['Soil_Type', 'Water_Frequency', 'Fertilizer_Type'], drop_first=True)
            model_columns = df_encoded_ref.columns.tolist()
        else:
            print("Growth Data CSV not found. Prediction might fail.")
    
    if os.path.exists("plant_disease.h5"):
        disease_model = tf.keras.models.load_model("plant_disease.h5")
        print("Plant disease model loaded.")

except Exception as e:
    print(f"Model loading error: {e}")

db.init_app(app)
api = Api(app, version='1.0', 
          title='Plant Disease and Growth Prediction API', 
          description='API for predicting plant diseases and growth milestones',
          doc='/docs')

# swagger model
user_model = api.model('User', {
    'id': fields.Integer(readonly=True),
    'username': fields.String(required=True),
    'email': fields.String(required=True),
    'password': fields.String()
})

plant_model = api.model('Plant', {
    'id': fields.Integer(readonly=True),
    'name': fields.String(required=True),
    'species': fields.String(),
    'user_id': fields.Integer(required=True)
})

disease_result_model = api.model('DiseaseResult', {
    'plant_id': fields.Integer,
    'confidence': fields.Float,
    'result': fields.String(attribute='disease_info.name', description='Disease Name')
})

growth_input_model = api.model('GrowthInput', {
    'soil_type': fields.String(required=True),
    'sunlight_hours': fields.Float(required=True),
    'water_frequency': fields.String(required=True),
    'fertilizer_type': fields.String(required=True),
    'temperature': fields.Float(required=True),
    'humidity': fields.Float(required=True)
})

upload_parser = api.parser()
upload_parser.add_argument('file', location='files', type=FileStorage, required=True)
upload_parser.add_argument('plant_id', location='form', type=int, required=True)

def seed_disease_types():
    if DiseaseType.query.first() is None:
        csv_path = 'disease_type.csv'
        if os.path.exists(csv_path):
            print(f"Seeding database from: {csv_path}")
            try:
                df = pd.read_csv(csv_path)
                for _, row in df.iterrows():
                    db.session.add(DiseaseType(name=row['name']))
                db.session.commit()
                print("Database seeding completed.")
            except Exception as e:
                print(f"CSV Error: {e}")
        else:
            print(f"Warning: '{csv_path}' not found. Database is empty!")

# endpoints
# 1. Resource: Users
@api.route('/users')
class UserList(Resource):
    # get: retrieves the entire user list
    @api.marshal_list_with(user_model) # all user json list
    def get(self): 
        return User.query.all() # select*from users
    
    # post: creates new resource
    @api.expect(user_model)
    @api.marshal_with(user_model) # json 
    def post(self):
        data = api.payload
        user = User(username=data['username'], email=data['email'], password=data.get('password',''))
        
        try:
            db.session.add(user) # wait
            db.session.commit() # record
            return user, 201
        except IntegrityError:
            db.session.rollback() # cancel
            api.abort(400, "This username or email address is registered.")

@api.route('/users/<int:id>')
@api.response(404,'user not found')
class UserResource(Resource):
    # get: retrieves the one user list
    @api.marshal_list(user_model)
    def get(self, id):
        return User.query.get_or_404(id) #select*from users where id
    
    #patch: updates the existing resource
    @api.expect(user_model, validate=False)
    @api.marshal_list(user_model)
    def patch(self, id): 
        user = User.query.get_or_404(id)
        data = api.payload

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

@api.route('/plants')
class PlantList(Resource):
    @api.marshal_list_with(plant_model)
    def get(self): return Plant.query.all()
    @api.expect(plant_model)
    @api.marshal_with(plant_model)
    def post(self):
        data = api.payload
        if not User.query.get(data['user_id']): return {'message': 'User not found'}, 404
        plant = Plant(name=data['name'], species=data.get('species'), user_id=data['user_id'])
        db.session.add(plant)
        db.session.commit()
        return plant, 201

@api.route('/check-disease')
class DiseaseCheckResource(Resource):
    @api.expect(upload_parser)
    @api.marshal_with(disease_result_model)
    def post(self):
        if not disease_model: api.abort(503, 'Model not loaded')
        
        args = upload_parser.parse_args()
        file = args['file']
        plant_id = args['plant_id']
        
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        
        # Prediction
        img = Image.open(path).resize((224, 224))
        img_array = np.array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        
        predictions = disease_model.predict(img_array)
        predicted_idx = np.argmax(predictions) 
        confidence = float(np.max(predictions))
        
        disease_type = DiseaseType.query.get(int(predicted_idx) + 1)
        
        if not disease_type:
            first_type = DiseaseType.query.first()
            if first_type:
                disease_type = first_type
            else:
                unknown = DiseaseType(name="Unknown Disease")
                db.session.add(unknown)
                db.session.commit()
                disease_type = unknown
            
        check = DiseaseCheck(plant_id=plant_id, image_path=path, disease_type_id=disease_type.id, confidence=confidence)
        db.session.add(check)
        db.session.commit()
        return check, 201

@api.route('/predict-growth')
class GrowthPredictionResource(Resource):
    @api.expect(growth_input_model, validate=True)
    def post(self):
        if not growth_model: api.abort(503, 'Growth model not loaded')
        if not model_columns: api.abort(500, "Reference columns not loaded")
        
        data = api.payload
        input_data = {
            'Soil_Type': data['soil_type'],
            'Sunlight_Hours': data['sunlight_hours'],
            'Water_Frequency': data['water_frequency'],
            'Fertilizer_Type': data['fertilizer_type'],
            'Temperature': data['temperature'],
            'Humidity': data['humidity']
        }

        input_df = pd.DataFrame([input_data])
        # One-Hot Encoding
        input_df = pd.get_dummies(input_df, columns=['Soil_Type', 'Water_Frequency', 'Fertilizer_Type'])
        input_df = input_df.reindex(columns=model_columns, fill_value=0)
        
        prediction = growth_model.predict(input_df)[0]
        return {'predicted_growth_milestone': int(prediction)}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_disease_types()
    app.run(debug=True)