from flask_restx import Namespace, Resource, fields
from app.extensions import db
from app.models import Plant, PlantCare
from datetime import datetime
import warnings

care_ns = Namespace('care', description='Plant care operations')

care_input_model = care_ns.model('PlantCareInput', {
    'plant_id': fields.Integer(required=True),
    'medicine_name': fields.String(required=True),
    'notes': fields.String,
    'growth_log_id': fields.Integer,
    'disease_check_id': fields.Integer
})

care_output_model = care_ns.model('PlantCare', {
    'id': fields.Integer,
    'plant_id': fields.Integer,
    'medicine_name': fields.String,
    'applied_at': fields.DateTime,
    'notes': fields.String,
    'related_growth_log': fields.Integer(attribute='growth_log_id'),
    'related_disease_check': fields.Integer(attribute='disease_check_id')
})

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

# 5. Resource: Plant Care
"""
it is a source that tracks plant growth or treatment methods used against disease
"""
@care_ns.route('/plant-cares')
class PlantCareList(Resource):
    # get: list all care history
    @care_ns.marshal_list_with(care_output_model)
    def get(self):
        return PlantCare.query.all()
    
    # post: add plant care
    @care_ns.expect(care_input_model)
    @care_ns.marshal_with(care_output_model)
    def post(self):
        data = care_ns.payload

        plant = Plant.query.get(data['plant_id'])
        if not plant:
            care_ns.abort(404, "plant not found")
        care = PlantCare(
            plant_id=data['plant_id'],
            medicine_name=data['medicine_name'],
            notes=data.get('notes'),
            growth_log_id=data.get('growth_log_id'),     
            disease_check_id=data.get('disease_check_id')
        )

        db.session.add(care)
        db.session.commit()
        return care, 201

@care_ns.route('/plant-cares/<int:id>')
@care_ns.response(404, 'care record not found')
class PlantCareResource(Resource):
    # get: retrieves the one care record
    @care_ns.marshal_with(care_input_model)
    def get(self,id):
        return PlantCare.query.get_or_404(id)
    
    # patch: update the care record 
    @care_ns.expect(care_input_model, validate=False)
    @care_ns.marshal_with(care_output_model)
    def patch(self, id):
        care = PlantCare.query.get_or_404(id)
        data = care_ns.payload
        if 'medicine_name' in data: care.medicine_name = data['medicine_name']
        if 'notes' in data: care.notes = data['notes']

        db.session.commit()
        return care
    
    # delete: delete the prediction record
    def delete(self, id):
        care = PlantCare.query.get_or_404(id)
        db.session.delete(care)
        db.session.commit()
        return '', 204

@care_ns.route('/plants/<int:plant_id>/cares')
class PlantCareHistory(Resource):
    @care_ns.marshal_list_with(care_output_model)
    def get(self, plant_id):
        plant = Plant.query.get_or_404(plant_id)
        cares= PlantCare.query.filter_by(plant_id=plant_id).order_by(PlantCare.applied_at.desc()).all()

        return cares