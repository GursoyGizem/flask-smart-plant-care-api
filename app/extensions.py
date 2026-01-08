from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api

db = SQLAlchemy()

api = Api(version='1.0', 
          title='Plant Disease and Growth Prediction API', 
          description='API for predicting plant diseases and growth milestones',
          doc='/docs')

# model load
growth_model = None
disease_model = None
model_columns = []