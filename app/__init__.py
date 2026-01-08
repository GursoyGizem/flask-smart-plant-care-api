from app import models
import os
from flask import Flask
import joblib
import pandas as pd
import tensorflow as tf

from app.extensions import db, api
from app.routes.user import user_ns
from app.routes.plant import plant_ns
from app.routes.growth_log import growth_ns
from app.routes.disease_check import disease_ns
from app.routes.plant_care import care_ns

def create_app(config_name='dev'):
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = 'super-secret-key'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'uploads'
    
    if config_name == 'test':
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plant_care.db'

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    db.init_app(app)
    api.init_app(app)

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

    api.add_namespace(user_ns, path='/')
    api.add_namespace(plant_ns, path='/')
    api.add_namespace(growth_ns, path='/')
    api.add_namespace(disease_ns, path='/')
    api.add_namespace(care_ns, path='/')

    return app

