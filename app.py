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
    # get: retrieves the one user
    @api.marshal_with(user_model)
    def get(self, id):
        return User.query.get_or_404(id) #select*from users where id
    
    #patch: updates the existing resource
    @api.expect(user_model, validate=False)
    @api.marshal_with(user_model)
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

# 2. Resource: Plants
"""
the user's plant list (name and species) is recorded in the plants resource
"""
@api.route('/plants')
class PlantList(Resource):
    # get: list all plants
    @api.marshal_list_with(plant_model)
    def get(self): 
        return Plant.query.all() # select*from plant
    
    # post: add new plant
    @api.expect(plant_model)
    @api.marshal_with(plant_model)
    def post(self):
        data = api.payload
        if not User.query.get(data['user_id']): 
            return {'message': 'User not found'}, 404
        
        plant = Plant(name=data['name'], 
                      species=data.get('species'), 
                      user_id=data['user_id'])
        
        db.session.add(plant)
        db.session.commit()
        return plant, 201
    
@api.route('/plants/<int:id>')
@api.response(404,'plant not found')
class PlantResource(Resource):
    # get: retrieves the one plant
    @api.marshal_with(plant_model)
    def get(self, id):
        return Plant.query.get_or_404(id)
    
    # patch: update plant information
    @api.expect(plant_model, validate=False)
    @api.marshal_with(plant_model)
    def patch(self, id):
        plant = Plant.query.get_or_404(id)
        data = api.payload

        if 'name' in data:
            plant.name = data['name']
        if 'species' in data:
            plant.species = data['species']

        db.session.commit()
        return plant
    
    # delete: delete the plant
    def delete(self, id):
        plant = Plant.query.get_or_404(id)
        db.session.delete(plant)
        db.session.commit()
        return '', 204
    
plant_filter_parser = api.parser()
plant_filter_parser.add_argument('species', type=str, required=False)

"""
Lists the plants of a specific user. Filters by type.
"""
@api.route('/users/<int:user_id>/plants')
@api.response(404,'user not found')
class UserPlantList(Resource):
    @api.expect(plant_filter_parser)
    @api.marshal_list_with(plant_model)
    def get(self, user_id):
        user = User.query.get_or_404(user_id)
        args = plant_filter_parser.parse_args()
        species_filter = args.get('species')
        query = Plant.query.filter_by(user_id=user_id)
        if species_filter:
            query = query.filter(Plant.species.ilike(f"%{species_filter}%"))

        return query.all()

# 3. Resource: Plant Growth Prediction
"""
the developed model is a resource that tracks plant growth prediction
"""
# swagger
growth_log_model = api.model('GrowthLog', {
    'id': fields.Integer(readonly=True),
    'plant_id': fields.Integer,
    'date': fields.DateTime,
    'predicted_milestone': fields.Integer,
    'soil_type': fields.String,
    'sunlight_hours': fields.Float,
    'water_frequency': fields.String,
    'fertilizer_type': fields.String,
    'temperature': fields.Float,
    'humidity': fields.Float
})

growth_input_model = api.model('GrowthInput',{
    'plant_id': fields.Integer,
    'soil_type': fields.String,
    'sunlight_hours': fields.Float,
    'water_frequency': fields.String,
    'fertilizer_type': fields.String,
    'temperature': fields.Float,
    'humidity': fields.Float
})

@api.route('/predict-growth')
class GrowthPredictionResource(Resource):
    # post: the model is run and saved to the database
    @api.expect(growth_input_model, validate=True)
    def post(self):
        if not growth_model: api.abort(503, 'Growth model not loaded')
        if not model_columns: api.abort(500, "Reference columns not loaded")
        
        data = api.payload

        plant = Plant.query.get(data['plant_id'])
        if not plant: api.abort(404, f"plant with id {data['plant_id']} not found")

        input_data = {
            'Soil_Type': data['soil_type'],
            'Sunlight_Hours': data['sunlight_hours'],
            'Water_Frequency': data['water_frequency'],
            'Fertilizer_Type': data['fertilizer_type'],
            'Temperature': data['temperature'],
            'Humidity': data['humidity']
        }

        try:
            input_df = pd.DataFrame([input_data])
            # One-Hot Encoding
            input_df = pd.get_dummies(input_df, columns=['Soil_Type', 'Water_Frequency', 'Fertilizer_Type'])
            input_df = input_df.reindex(columns=model_columns, fill_value=0)

            prediction = growth_model.predict(input_df)[0]
            prediction_val = int(prediction)

            new_log = GrowthLog(
                plant_id = data['plant_id'],
                soil_type = data['soil_type'],
                sunlight_hours = data['sunlight_hours'],
                water_frequency = data['water_frequency'],
                fertilizer_type = data['fertilizer_type'],
                temperature = data['temperature'],
                humidity = data['humidity'],
                predicted_milestone = prediction_val
                )

            db.session.add(new_log)
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            api.abort(500, str(e))
    
@api.route('/growth-logs')
class GrowthLogList(Resource):
    # get:
    @api.marshal_list_with(growth_log_model)
    def get(self):
        return GrowthLog.query.all()
    
@api.route('/growth-logs/<int:id>')
@api.response(404,'growth log not found')
class GrowthLogResource(Resource):
    # get: retrieves the one prediction record
    @api.marshal_with(growth_log_model)
    def get(self,id):
        return GrowthLog.query.get_or_404(id)
    
    # patch: update the prediction record 
    @api.expect(growth_log_model, validate=False)
    @api.marshal_with(growth_log_model)
    def patch(self, id):
        log = GrowthLog.query.get_or_404(id)
        data = api.payload

        if 'predicted_milestone' in data:
            log.predicted_milestone = data['predicted_milestone']

        db.session.commit()
        return log
    
    # delete: delete the prediction record
    def delete(self, id):
        log = GrowthLog.query.get_or_404(id)
        db.session.delete(log)
        db.session.commit()
        return '', 204
    
@api.route('/plants/<int:plant_id>/growth-logs')
class PlantGrowthHistory(Resource):
    # get: lists all predictions for a specific plant
    @api.marshal_list_with(growth_log_model)
    def get(self, plant_id):
        plant = Plant.query.get_or_404(plant_id)
        return plant.growth_logs

# 4. Resource: Plant Disease Check
"""
the plant's disease is detected
"""

#swagger
disease_type_model = api.model('DiseaseType',{
    'id': fields.Integer,
    'name': fields.String
})

disease_check_model = api.model('DiseaseCheck',{
    'id': fields.Integer(readonly=True),
    'plant_id': fields.Integer,
    'image_path': fields.String,
    'confidence': fields.Float,
    'created_at': fields.DateTime,
    'disease_type_id': fields.Integer,
    'disease_name': fields.String(attribute='disease_info.name')
})

@api.route('/check-disease')
class DiseaseCheckCreate(Resource):
    @api.expect(upload_parser)
    @api.marshal_with(disease_check_model)
    # post: performs an AI prediction, and saves the result to a database
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
            
        check = DiseaseCheck(
            plant_id=plant_id, 
            image_path=path, 
            disease_type_id=disease_type.id, 
            confidence=confidence
            )
        
        db.session.add(check)
        db.session.commit()
        return check, 201

@api.route('/disease-checks')
class DiseaseCheckList(Resource):
    # get: it lists all disease in the system
    @api.marshal_list_with(disease_check_model)
    def get(self):
        return DiseaseCheck.query.all()
    
@api.route('/disease-checks/<int:id>')
@api.response(404, 'check not found')
class DiseaseCheckResource(Resource):
     # get: retrieves the one prediction record
    @api.marshal_with(disease_check_model)
    def get(self,id):
        return DiseaseCheck.query.get_or_404(id)
    
    # patch: update the prediction record 
    @api.expect(disease_check_model, validate=False)
    def patch(self, id):
        check = DiseaseCheck.query.get_or_404(id)
        data = api.payload

        if 'disease_type_id' in data:
            dtype = DiseaseType.query.get(data['disease_type_id'])
            if dtype:
                check.disease_type_id = data['disease_type_id']
                db.session.commit()
            else:
                api.abort(400,"invalid disease type id")

        return check
    
    # delete: delete the prediction record
    def delete(self, id):
        check = DiseaseCheck.query.get_or_404(id)
        db.session.delete(check)
        db.session.commit()
        return '', 204
    
@api.route('/plants/<int:plant_id>/disease-checks')
class PlantDiseaseHistory(Resource):
    # get: it lists the disease history of a specific plant
    @api.marshal_list_with(disease_check_model)
    def get(self, plant_id):
        plant = Plant.query.get_or_404(plant_id)
        checks = DiseaseCheck.query.filter_by(plant_id=plant_id).order_by(DiseaseCheck.created_at.desc()).all()
        
        return checks  

@api.route('/disease-checks')
class DiseaseTypeList(Resource):
    # get: it lists all the types of diseases recognized by the system
    @api.marshal_list_with(disease_type_model)
    def get(self):
        return DiseaseType.query.all()
    
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_disease_types()
    app.run(debug=True)