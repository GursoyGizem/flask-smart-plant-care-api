import pandas as pd
from datetime import datetime
import warnings
from flask_restx import Namespace, Resource, fields
from app import extensions
from app.extensions import db, growth_model, model_columns
from app.models import GrowthLog, Plant

growth_ns = Namespace('growth', description='Plant growth log operations')

growth_log_model = growth_ns.model('GrowthLog', {
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

growth_input_model = growth_ns.model('GrowthInput',{
    'plant_id': fields.Integer(required=True),
    'soil_type': fields.String(required=True),
    'sunlight_hours': fields.Float(required=True),
    'water_frequency': fields.String(required=True),
    'fertilizer_type': fields.String(required=True),
    'temperature': fields.Float(required=True),
    'humidity': fields.Float(required=True)
})

def prepare_prediction_dataframe(input_data, model_columns):
    input_df = pd.DataFrame([input_data])
    input_df = pd.get_dummies(input_df, columns=['Soil_Type', 'Water_Frequency', 'Fertilizer_Type']) # Dummy eklendi
    input_df = input_df.reindex(columns=model_columns, fill_value=0)
    return input_df

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

# 3. Resource: Plant Growth Prediction
"""
the developed model is a resource that tracks plant growth prediction
"""
@growth_ns.route('/predict-growth')
class GrowthPredictionResource(Resource):
    # post: the model is run and saved to the database
    @growth_ns.expect(growth_input_model, validate=True)
    def post(self):
        if not extensions.growth_model: growth_ns.abort(503, 'Growth model not loaded')
        if not extensions.model_columns: growth_ns.abort(500, "Reference columns not loaded")

        data = growth_ns.payload

        plant = Plant.query.get(data['plant_id'])
        if not plant: growth_ns.abort(404, f"plant with id {data['plant_id']} not found")

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
            input_df = input_df.reindex(columns=extensions.model_columns, fill_value=0)

            prediction = extensions.growth_model.predict(input_df)[0]
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
            growth_ns.abort(500, str(e))

@growth_ns.route('/growth-logs')
class GrowthLogList(Resource):
    # get: retrieves the all prediction record
    @growth_ns.marshal_list_with(growth_log_model)
    def get(self):
        return GrowthLog.query.all()

@growth_ns.route('/growth-logs/<int:id>')
@growth_ns.response(404,'growth log not found')
class GrowthLogResource(Resource):
    # get: retrieves the one prediction record
    @growth_ns.marshal_with(growth_log_model)
    def get(self,id):
        return GrowthLog.query.get_or_404(id)
    
    # patch: update the prediction record 
    @growth_ns.expect(growth_log_model, validate=False)
    @growth_ns.marshal_with(growth_log_model)
    def patch(self, id):
        log = GrowthLog.query.get_or_404(id)
        data = growth_ns.payload
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

@growth_ns.route('/plants/<int:plant_id>/growth-logs')
class PlantGrowthHistory(Resource):
    # get: lists all predictions for a specific plant
    @growth_ns.marshal_list_with(growth_log_model)
    def get(self, plant_id):
        plant = Plant.query.get_or_404(plant_id)
        return plant.growth_logs