import os
import re
import numpy as np
from PIL import Image
from flask_restx import Namespace, Resource, fields
from flask import current_app
import pandas as pd
from datetime import datetime
import warnings
from app import extensions
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from app.extensions import db, disease_model
from app.models import DiseaseCheck, DiseaseType, Plant

disease_ns = Namespace('disease', description='Plant disease check operations')

disease_type_model = disease_ns.model('DiseaseType',{
    'id': fields.Integer,
    'name': fields.String
})

disease_check_model = disease_ns.model('DiseaseCheck', {
    'id': fields.Integer(readonly=True),
    'plant_id': fields.Integer,
    'image_path': fields.String,
    'confidence': fields.Float,
    'created_at': fields.DateTime,
    'disease_type_id': fields.Integer,
    'disease_name': fields.String(attribute='disease_info.name')
})

# upload image parser
upload_parser = disease_ns.parser()
# files 
upload_parser.add_argument('file', location='files', type=FileStorage, required=True)
# form for other data sent along with the file
upload_parser.add_argument('plant_id', location='form', type=int, required=True)

def format_disease_name(raw_name):
    if "___" in raw_name:
        parts = raw_name.split("___")
        species = parts[0]
        disease = parts[1].replace("_", " ")
        return f"{species} - {disease}"
    return raw_name

def predict_disease(confidence):
    if confidence > 0.80:
        return "High Confidence"
    elif 0.50 <= confidence <= 0.80:
        return "Medium Confidence"
    else:
        return "Unknown"

def validate_image_format(filename):
    if not filename or "." not in filename:
        return False
    
    allowed_extensions = {'.jpg', '.jpeg', '.png'}
    ext = os.path.splitext(filename)[1].lower()
    
    return ext in allowed_extensions

def normalize_name(name):
    if not name:
        return ""
    
    clean_name = re.sub(r'[^\w\s]', '', name)

    return clean_name.strip().title()

def seed_disease_types():
    if DiseaseType.query.first() is None:
        csv_path = 'disease_types.csv'
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
            print(f"Warning: '{csv_path}' not found.")

def parse_csv_date(date_str):
    if not date_str:
        return None
        
    formats = ["%Y-%m-%d", "%d/%m/%Y"] 
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt > datetime.now():
                warnings.warn(f"Future date detected: {date_str}", UserWarning)
            return dt
        except ValueError:
            continue
            
    return None 

# 4. Resource: Plant Disease Check
"""
the plant's disease is detected
"""
@disease_ns.route('/check-disease')
class DiseaseCheckCreate(Resource):
    def get_or_create_unknown(self):
        unknown = DiseaseType.query.filter_by(name="Unknown Disease").first()
        if not unknown:
            unknown = DiseaseType(name="Unknown Disease")
            db.session.add(unknown)
            db.session.commit()
        return unknown
    
    @disease_ns.expect(upload_parser)
    @disease_ns.marshal_with(disease_check_model)
    # post: performs an AI prediction, and saves the result to a database
    def post(self):
        if not extensions.disease_model: disease_ns.abort(503, 'Model not loaded')
        
        args = upload_parser.parse_args()
        file = args['file']
        plant_id = args['plant_id']

        if not validate_image_format(file.filename):
            disease_ns.abort(400, "Invalid file format.")

        plant = Plant.query.get(plant_id)
        if not plant: disease_ns.abort(404, "plant not found")

        all_diseases = DiseaseType.query.all()
        supported_species = set([d.name.split('___')[0] for d in all_diseases])
        if plant.species and plant.species.capitalize() not in supported_species:
            return {
                'message': f"Disease detection for '{plant.species}' is not supported yet. Supported types: {list(supported_species)}"
            }, 400
        
        filename = secure_filename(file.filename)
        path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        
        # Prediction
        try:
            img = Image.open(path).resize((224, 224))
        except Exception:
            return {'message': 'Invalid image file.'}, 400

        img_array = np.array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        
        predictions = extensions.disease_model.predict(img_array)
        predicted_idx = np.argmax(predictions) 
        confidence = float(np.max(predictions))
        
        if confidence < 0.50:
            disease_type = self.get_or_create_unknown()
        else:
            disease_type = DiseaseType.query.get(int(predicted_idx)+1)

        check = DiseaseCheck(
            plant_id=plant_id, 
            image_path=path, 
            disease_type_id=disease_type.id, 
            confidence=confidence
            )
        
        db.session.add(check)
        db.session.commit()
        return check, 201

@disease_ns.route('/disease-checks')
class DiseaseCheckList(Resource):
    # get: it lists all disease in the system
    @disease_ns.marshal_list_with(disease_check_model)
    def get(self):
        return DiseaseCheck.query.all()

@disease_ns.route('/disease-checks/<int:id>')
@disease_ns.response(404, 'check not found')
class DiseaseCheckResource(Resource):
     # get: retrieves the one prediction record
    @disease_ns.marshal_with(disease_check_model)
    def get(self,id):
        return DiseaseCheck.query.get_or_404(id)
    
    # patch: update the prediction record 
    @disease_ns.expect(disease_check_model, validate=False)
    @disease_ns.marshal_with(disease_check_model)
    def patch(self, id):
        check = DiseaseCheck.query.get_or_404(id)
        data = disease_ns.payload
        if 'disease_type_id' in data:
            dtype = DiseaseType.query.get(data['disease_type_id'])
            if dtype:
                check.disease_type_id = data['disease_type_id']
                db.session.commit()
            else:
                disease_ns.abort(400,"invalid disease type id")

        return check
    
    # delete: delete the prediction record
    def delete(self, id):
        check = DiseaseCheck.query.get_or_404(id)
        db.session.delete(check)
        db.session.commit()
        return '', 204

@disease_ns.route('/plants/<int:plant_id>/disease-checks')
class PlantDiseaseHistory(Resource):
    # get: it lists the disease history of a specific plant
    @disease_ns.marshal_list_with(disease_check_model)
    def get(self, plant_id):
        plant = Plant.query.get_or_404(plant_id)
        checks = DiseaseCheck.query.filter_by(plant_id=plant_id).order_by(DiseaseCheck.created_at.desc()).all()
        
        return checks  

@disease_ns.route('/disease-type')
class DiseaseTypeList(Resource):
    # get: it lists all the types of diseases recognized by the system
    @disease_ns.marshal_list_with(disease_type_model)
    def get(self):
        return DiseaseType.query.all()
