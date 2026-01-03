from extensions import db
from datetime import datetime

# users table
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    
    plants = db.relationship('Plant', backref='owner', lazy=True, cascade="all, delete-orphan")

# plant table
class Plant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    species = db.Column(db.String(120))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    growth_logs = db.relationship('GrowthLog', backref='plant', lazy=True)
    disease_checks = db.relationship('DiseaseCheck', backref='plant', lazy=True)

# growth log table
class GrowthLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    soil_type = db.Column(db.String(50))
    sunlight_hours = db.Column(db.Float)
    water_frequency = db.Column(db.String(50))
    fertilizer_type = db.Column(db.String(50))
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    predicted_milestone = db.Column(db.Integer)

# plant diease folder 
class DiseaseType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    checks = db.relationship('DiseaseCheck', backref='disease_info', lazy=True)

# plant disease check table
class DiseaseCheck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(255)) 
    
    disease_type_id = db.Column(db.Integer, db.ForeignKey('disease_type.id'), nullable=False)
    confidence = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)

# plant care tips table
class PlantCare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_species = db.Column(db.String(100)) 
    tip_text = db.Column(db.Text, nullable=False)