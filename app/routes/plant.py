from flask_restx import Namespace, Resource, fields
from app.extensions import db
from app.models import Plant, User

plant_ns = Namespace('plants', description='Plant operations')

plant_model = plant_ns.model('Plant', {
    'id': fields.Integer(readonly=True),
    'name': fields.String(required=True),
    'species': fields.String(),
    'user_id': fields.Integer(required=True)
})

# plant filter parser
plant_filter_parser = plant_ns.parser()
plant_filter_parser.add_argument('species', type=str, required=False)

def validate_plant(plant_id):
    return Plant.query.get(plant_id) is not None

# 2. Resource: Plants
"""
the user's plant list (name and species) is recorded in the plants resource
"""
@plant_ns.route('/plants')
class PlantList(Resource):
    # get: list all plants
    @plant_ns.marshal_list_with(plant_model)
    def get(self): 
        return Plant.query.all() # select*from plant
    
    # post: add new plant
    @plant_ns.expect(plant_model)
    @plant_ns.marshal_with(plant_model)
    def post(self):
        data = plant_ns.payload
        if not User.query.get(data['user_id']): 
            plant_ns.abort(404, {'message': 'User not found'})
        
        plant = Plant(name=data['name'], 
                      species=data.get('species'), 
                      user_id=data['user_id'])
        
        db.session.add(plant)
        db.session.commit()
        return plant, 201

@plant_ns.route('/plants/<int:id>')
@plant_ns.response(404,'plant not found')
class PlantResource(Resource):
    # get: retrieves the one plant
    @plant_ns.marshal_with(plant_model)
    def get(self, id):
        return Plant.query.get_or_404(id)
    
    # patch: update plant information
    @plant_ns.expect(plant_model, validate=False)
    @plant_ns.marshal_with(plant_model)
    def patch(self, id):
        plant = Plant.query.get_or_404(id)
        data = plant_ns.payload
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
    
"""
Lists the plants of a specific user. Filters by type.
"""
@plant_ns.route('/users/<int:user_id>/plants')
@plant_ns.response(404,'user not found')
class UserPlantList(Resource):
    @plant_ns.expect(plant_filter_parser)
    @plant_ns.marshal_list_with(plant_model)
    def get(self, user_id):
        user = User.query.get_or_404(user_id)
        args = plant_filter_parser.parse_args()
        species_filter = args.get('species')
        query = Plant.query.filter_by(user_id=user_id)
        if species_filter:
            query = query.filter(Plant.species.ilike(f"%{species_filter}%"))

        return query.all()
