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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)

    growth_logs = db.relationship('GrowthLog', backref='plant', lazy=True, cascade="all, delete-orphan")
    disease_checks = db.relationship('DiseaseCheck', backref='plant', lazy=True, cascade="all, delete-orphan")
    cares = db.relationship('PlantCare', backref='plant', lazy=True, cascade="all, delete-orphan")

# growth log table
class GrowthLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id', ondelete="CASCADE"), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    soil_type = db.Column(db.String(50), nullable=False)
    sunlight_hours = db.Column(db.Float, nullable=False)
    water_frequency = db.Column(db.String(50), nullable=False)
    fertilizer_type = db.Column(db.String(50), nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    predicted_milestone = db.Column(db.Integer, nullable=False)

# plant diease folder 
class DiseaseType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    checks = db.relationship('DiseaseCheck', backref='disease_info', lazy=True)

# plant disease check table
class DiseaseCheck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id', ondelete="CASCADE"), nullable=False)
    disease_type_id = db.Column(db.Integer, db.ForeignKey('disease_type.id'), nullable=False)
    
    image_path = db.Column(db.String(255)) 
    confidence = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# plant care table
class PlantCare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id', ondelete="CASCADE"), nullable=False)

    medicine_name = db.Column(db.String(255))
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    growth_log_id = db.Column(db.Integer, db.ForeignKey('growth_log.id'), nullable=True)
    disease_check_id = db.Column(db.Integer, db.ForeignKey('disease_check.id'), nullable=True)

    growth_info = db.relationship('GrowthLog', backref='treatments')
    disease_info = db.relationship('DiseaseCheck', backref='treatments')