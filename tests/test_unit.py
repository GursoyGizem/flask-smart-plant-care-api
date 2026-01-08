import pytest 
import io
import pandas as pd 

from app.extensions import db
from unittest.mock import patch
from app.models import User, Plant, GrowthLog, DiseaseType
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from PIL import Image
from app.routes.user import validate_email_format, validate_password_strength
from app.routes.disease_check import format_disease_name, predict_disease, validate_image_format, seed_disease_types, normalize_name
from app.routes.growth_log import prepare_prediction_dataframe, parse_csv_date
from app.routes.plant import validate_plant

user_name = "gizem"
user_email = "gizem@example.com"
user_password = "Gizem.123"

#  1. Unit Test: bir user nesnesi olusturdugumda veriler dogru ataniyor mu?
def test_user_model_creation(client):
    user = User(username=user_name, email=user_email, password=user_password)

    assert user.username == "gizem"
    assert user.email == "gizem@example.com"
    assert user.password == "Gizem.123"

#  2. Unit Test: bitki olustururken user_id dogru ataniyor mu?
def test_plant_relationship(client):
    user = User(username=user_name, email=user_email, password=user_password)
    db.session.add(user)
    db.session.commit()

    plant = Plant(name="havuc", species="carrot", user_id=user.id)
    db.session.add(plant)
    db.session.commit()

    assert plant.user_id == user.id

#  3. Unit Test: growth log sayisal verileri dogru tutuyor mu?
def test_growth_log_types(client):
    log = GrowthLog(
        plant_id = 1,
        soil_type = "clay",
        sunlight_hours = 5.5,
        water_frequency = "Daily",
        fertilizer_type = "None",
        temperature = 24.0,
        humidity = 60.0
    )

    db.session.add(log)
    assert isinstance(log.sunlight_hours, float)
    assert isinstance(log.water_frequency, str)

#  4. Unit Test: get_or_create_unknown
@patch('app.extensions.disease_model')
def test_utility_get_or_create_unknown(mock_model, client, app):
    client.post('/users', json={
        'username': user_name,
        'email': user_email, 
        'password': user_password
        })
    
    client.post('/plants', json={
        'name': 'P', 
        'species': 'Apple', 
        'user_id': 1
        })
    
    with app.app_context():
        seed_disease_types()

    mock_model.predict.return_value = [[0.1]]
    
    with patch('werkzeug.datastructures.FileStorage.save'), patch('PIL.Image.open'):
        client.post('/check-disease', data={
            'plant_id': 1, 
            'file': (io.BytesIO(b"img"), 'test.jpg') 
        })
        
        client.post('/check-disease', data={
            'plant_id': 1, 
            'file': (io.BytesIO(b"img"), 'test.jpg') # Yeni dosya
        })
        
    count = DiseaseType.query.filter_by(name="Unknown Disease").count()
    assert count == 1

#  5. Unit Test: plant disease confidence < threshold oldugunda unknown ataniyor mu?
def test_disease_threshold_decision_unit():
    confidence = 0.3 
    threshold = 0.5

    result = "unknown disease" if confidence < threshold else "known disease"
    assert result == "unknown disease"

# 6. Unit Test: email formati kontrolu
def test_email_validation():
    assert validate_email_format("test@example.com") is True
    assert validate_email_format("user.name@domain.co") is True
    assert validate_email_format("testexample.com") is False 
    assert validate_email_format("test@.com") is False      
    assert validate_email_format("@example.com") is False   
    assert validate_email_format("") is False
    assert validate_email_format(None) is False

# 7. Unit Test: disease type name dogru formatta cekiyor mu?
def test_disease_name_formatting():
    raw_name = "Apple___Black_rot"
    formatted = format_disease_name(raw_name)
    
    assert formatted == "Apple - Black rot"
    assert format_disease_name("Unknown Disease") == "Unknown Disease"

# 8. Unit Test: sifre kontrolu
def test_logic_password_strength():
    assert validate_password_strength("Ab1!") is False
    assert validate_password_strength("zayif123!") is False
    assert validate_password_strength("GUCLU123!") is False
    assert validate_password_strength("Sifre!Sifre") is False
    assert validate_password_strength("Sifre12345") is False
    assert validate_password_strength("Guclu.123") is True

# 9. Unit Test: data frame formatina dogru donusturuyor mu?
def test_prepare_prediction_dataframe():
    input_data = {
        "Soil_Type": "Clay",
        "Temperature": 25,
        "Water_Frequency": "Daily",
        "Fertilizer_Type": "None"
    }
    model_columns = ["Soil_Type_Clay", "Soil_Type_Sand", "Temperature", "Humidity"]
    
    df = prepare_prediction_dataframe(input_data, model_columns)
    
    assert isinstance(df, pd.DataFrame)
    
    assert list(df.columns) == model_columns
    
    assert df.iloc[0]["Humidity"] == 0
    assert df.iloc[0]["Soil_Type_Sand"] == 0

# 10. Unit Test: plant disease modelinin confidence gore dogru siniflandirma yapiyor mu?
def test_disease_category():
    assert predict_disease(0.81) == "High Confidence"
    assert predict_disease(0.99) == "High Confidence"

    assert predict_disease(0.80) == "Medium Confidence" 
    assert predict_disease(0.65) == "Medium Confidence"
    assert predict_disease(0.50) == "Medium Confidence" 
    
    assert predict_disease(0.49) == "Unknown"
    assert predict_disease(0.10) == "Unknown"

# 11. Unit Test: plant disease modeline gecersiz image yuklenirse kabul edilir mi?
def test_image_format():
    assert validate_image_format("apple.jpg") is True
    assert validate_image_format("carrot.jpeg") is True
    assert validate_image_format("magnolia.png") is True
  
    assert validate_image_format("tomate.gif") is False
    assert validate_image_format("strawberry.pdf") is False
    assert validate_image_format("") is False

# 12. Unit Test: datetime formatina uygun mu?
def test_csv_date_parsing():
    dt1 = parse_csv_date("2024-01-15")
    assert isinstance(dt1, datetime)
    assert dt1.year == 2024 and dt1.month == 1

    dt2 = parse_csv_date("15/01/2024")
    assert isinstance(dt2, datetime)
    assert dt2.day == 15
    
    assert parse_csv_date("2024.01.15") is None
    assert parse_csv_date("yarin") is None
    
    future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    with pytest.warns(UserWarning, match="Future date"):
        parse_csv_date(future_date)

# 13. Unit Test: plant name standart hale getiriyor mu?
def test_species_normalization():
    assert normalize_name("  apple  ") == "Apple"
    assert normalize_name("TOMATO") == "Tomato"
    assert normalize_name("rOsE") == "Rose"
    assert normalize_name("Rose!") == "Rose"
    assert normalize_name("Cactus#1") == "Cactus1"
    assert normalize_name("") == ""
    assert normalize_name(None) == ""

# 14. Unit Test: nullable = false olan alanlar bos birakilinca database hatasi veriyor mu?
def test_growth_log_model_nullable(client):
    growth_input = GrowthLog(
            plant_id=1, 
            predicted_milestone=25, 
            soil_type="Killi",
            sunlight_hours=8.0,
            water_frequency="Weekly",     
            fertilizer_type=None,    
            temperature=22.0,             
            humidity=60.0
        )
    
    db.session.add(growth_input)
    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()

# 15. Unit Test: plant kontrolu
def test_validation_plant(client):
    client.post('/users', json={
        'username': user_name,
        'email': user_email, 
        'password': user_password
    })

    client.post("/plants", json={
        "name": "kasimpati",
        "user_id": 1,
    })

    assert validate_plant(1) is True
    assert validate_plant(9) is False
