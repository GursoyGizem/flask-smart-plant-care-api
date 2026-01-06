import pytest 
import io
import pandas as pd 

from app import app, db, seed_disease_types, validate_email_format, validate_password_strength, format_disease_name, prepare_prediction_dataframe, predict_disease, validate_image_format, parse_csv_date, normalize_name, validate_plant
from unittest.mock import patch, MagicMock
from models import User, Plant, GrowthLog, DiseaseType, PlantCare
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

user_name = "gizem"
user_email = "gizem@example.com"
user_password = "Gizem.123"

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        seed_disease_types()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

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
@patch('app.disease_model')
def test_utility_get_or_create_unknown(mock_model, client):
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

# 1. Integration Test: growth log gecersiz sayisal veri turu girilince hata veriyor mu?
def test_validation_growth_log_data_type(client):
    plant_input = {
        "plant_id": 1,
        "soil_type": "clay",
        "sunlight_hours": 5.5,
        "water_frequency": "Daily",
        "fertilizer_type": "None",
        "temperature": "otuz derece",
        "humidity": 60.0
    }

    response = client.post("/predict-growth", json=plant_input)

    assert response.status_code == 400
    assert "temperature" in str(response.json) or "errors" in str(response.json) 

# 2. Intregration Test: aynı email adresiyle ikinci kez kayıt olunabiliyor mu?
def test_create_user_duplicate_email(client):
    user =client.post('/users', json={
        'username': user_name,
        'email': user_email, 
        'password': user_password
    })

    assert user.status_code == 201

    user_duplicate = client.post('/users', json={
        "username": "nur gizem",
        "email": user_email,
        "password": "giZem123."
    })

    assert user_duplicate.status_code == 400
    assert "registered" in user_duplicate.json["message"]

# 3. Intregration Test: User listesi çekildiğinde şifreler gizleniyor mu?
def test_user_hides_password(client):
    client.post('/users', json={
        'username': user_name,
        'email': user_email, 
        'password': user_password
        })

    hides_user = client.get("/users")
    assert hides_user.status_code == 200

    data = hides_user.json
    assert "username" in data[0]
    assert "password" not in data[0]

# 4. Intregration Test: User bitki türlerini filtreleme yapabiliyor mu?
def test_user_plants_filter(client):
    client.post('/users', json={
        'username': user_name,
        'email': user_email, 
        'password': user_password
        })

    client.post("/plants", json={
        "name": "beyaz buyuk cicekli manolya",
        "user_id": 1,
        "species": "southern"
    })

    client.post("/plants", json={
        "name": "pembe buyuk cicekli manolya",
        "user_id": 1,
        "species": "southern"
    })

    client.post("/plants", json={
        "name": "beyaz kobusi manolya",
        "user_id": 1,
        "species": "kobus"
    })
    
    client.post("/plants", json={
        "name": "pembe kobusi manolya",
        "user_id": 1,
        "species": "kobus"
    })

    plant_species = client.get("/users/1/plants?species=southern")
    assert plant_species.status_code == 200

    data = plant_species.json
    assert "kobus" not in str(data)

# 5. Intregration Test: bir bitkiye ait growth logs dogru listeleniyor mu?
def test_plant_growth_history(client):
    client.post('/users', json={
        'username': user_name,
        'email': user_email, 
        'password': user_password
        })

    client.post("/plants", json={
        "name": "akasya",
        "user_id": 1
    })

    with app.app_context():
        log1 = GrowthLog(
            plant_id = 1,
            predicted_milestone=10, 
            soil_type="Kumlu",
            sunlight_hours=5.0,
            water_frequency="Daily",      
            fertilizer_type="None",       
            temperature=25.0,             
            humidity=50.0
        )

        log2 = GrowthLog(
            plant_id=1, 
            predicted_milestone=25, 
            soil_type="Killi",
            sunlight_hours=8.0,
            water_frequency="Weekly",     
            fertilizer_type="Organic",    
            temperature=22.0,             
            humidity=60.0
        )

        db.session.add(log1)
        db.session.add(log2)
        db.session.commit()

    plant_list = client.get("/plants/1/growth-logs")
    assert plant_list.status_code == 200

    data = plant_list.json
    assert len(data) == 2

# 6. Intregration Test: Plant Care History cekildiginde en son eklenen kayıt en uste geliyor mu?
def test_plant_care_history_sort(client):
    client.post('/users', json={
        'username': user_name,
        'email': user_email, 
        'password': user_password
        })

    client.post("/plants", json={
        "name": "domates",
        "user_id": 1
    })

    # ilk uygulanan tedavi
    client.post('/plant-cares', json={
        "plant_id": 1,
        "medicine_name": "azoxystrobin",
        "notes": "domates mildiyösü"
    })

    # ikinci uygulanan tedavi
    client.post('/plant-cares', json={
        "plant_id": 1,
        "medicine_name": "propineb",
        "notes": "domates mildiyösü"
    })

    plant_list = client.get("/plants/1/cares")
    assert plant_list.status_code == 200

    data = plant_list.json
    assert data[0]['medicine_name'] == "propineb"
    assert data[1]['medicine_name'] == "azoxystrobin"

# 7. Intregration Test: model yuklenmemisse sistem hata veriyor mu?
def test_predict_growth_model(client):
    input_data = {
        "plant_id": 1,
        "soil_type": "Kumlu",
        "sunlight_hours": 5.0,
        "water_frequency": "Daily",
        "fertilizer_type": "None",
        "temperature": 25.0,
        "humidity": 50.0
    }

    with patch("app.growth_model", None):
        response1 = client.post("/predict-growth", json = input_data)
        assert response1.status_code == 503

    with patch("app.disease_model", None):
        response2 = client.post("check-disease", json = {"plant_id": 1})
        assert response2.status_code == 503

# 8. Intregration Test:: disease plant modelinin gormedigi bir hastaligi kullanici vermek istediginde sistem hata veriyor mu?
@patch("app.disease_model")
def test_check_disease_unsupported_species(mock_model, client):
    with app.app_context():
        db.session.query(DiseaseType).delete()
        db.session.commit()
        seed_disease_types()

    client.post('/users', json={
        'username': user_name,
        'email': user_email, 
        'password': user_password
        })
    
    client.post("/plants", json={
        "name": "Dikenli", 
        "species": "Kaktus", 
        "user_id": 1
        })

    fake_file = (io.BytesIO(b"data"), 'kaktus.jpg')

    with patch('werkzeug.datastructures.FileStorage.save'), patch('PIL.Image.open'):
        response = client.post('/check-disease', data={
            'plant_id': 1,
            'file': fake_file
        }, content_type='multipart/form-data')

    assert response.status_code == 400
    assert mock_model.predict.called == False

# 9. Intregration Test: bir user silindiginde ona ait olan bitkiler de otomatik siliniyor mu?
def test_delete_user_cascades_plant(client):
    client.post('/users', json={
        'username': user_name,
        'email': user_email, 
        'password': user_password
        })

    client.post('/plants',json={
        "name": "kasimpati",
        "user_id": 1
    })

    check_plant = client.get("/plants/1")
    assert check_plant.status_code == 200

    delete_user = client.delete("/users/1")
    assert delete_user.status_code == 204

    plant_nope = client.get("/plants/1")
    assert plant_nope.status_code == 404

# 10. Integration Test: user http metodu 
def test_user_http(client):
    user = {"username": user_name, "email": user_email, "password": user_password}

    res_post = client.post("/users", json=user)
    assert res_post.status_code == 201

    user_id = res_post.json["id"]

    res_get = client.get(f"/users/{user_id}")
    assert res_get.status_code == 200
    assert res_get.json["username"] == "gizem"

    res_patch = client.patch(f"/users/{user_id}", json={"username": "nur gizem"})
    assert res_patch.status_code == 200
    assert res_patch.json["username"] == "nur gizem"
 
    res_del = client.delete(f"/users/{user_id}")
    assert res_del.status_code == 204

    res = client.get(f"/users/{user_id}")
    assert res.status_code == 404
    
# 11. Integration Test: plant http metodu
def test_plant_http(client):
    client.post('/users', json={'username': user_name, 'email': user_email, 'password': user_password})
    
    res_post = client.post("/plants", json={
        "name": "kasimpati",
        "species": None,
        "user_id": 1
    })
    assert res_post.status_code == 201

    plant_id = res_post.json["id"]

    res_get = client.get(f"/plants/{plant_id}")
    assert res_get.status_code == 200
    assert res_get.json["name"] == "kasimpati"

    res_patch = client.patch(f"/plants/{plant_id}", json={"name": "rose"})
    assert res_patch.status_code == 200
    assert res_patch.json["name"] == "rose"
 
    res_del = client.delete(f"/plants/{plant_id}")
    assert res_del.status_code == 204

    res = client.get(f"/plants/{plant_id}")
    assert res.status_code == 404

# 12. Integration Test: plant growth log http metodu
def test_plant_growth_log_http(client):
    client.post('/users', json={'username': user_name, 'email': user_email, 'password': user_password})
    client.post("/plants", json={"name": "kasimpati", "species": None, "user_id": 1})

    with patch("app.growth_model") as mock_model:
        mock_model.predict.return_value = [1] 
        with patch("app.model_columns", ["Soil_Type_Clay", "Water_Frequency_Daily"]):
            input_data = {
                "plant_id": 1,
                "soil_type": "Clay",
                "sunlight_hours": 8.0,
                "water_frequency": "Daily",
                "fertilizer_type": "None",
                "temperature": 25.0,
                "humidity": 60.0
            }
            client.post("/predict-growth", json=input_data)
    
    log_id = client.get("/growth-logs").json[0]["id"]

    res_get = client.get(f"/growth-logs/{log_id}")
    assert res_get.status_code == 200
    assert res_get.json["predicted_milestone"] == 1

    res_patch = client.patch(f"/growth-logs/{log_id}", json={"predicted_milestone": 0})
    assert res_patch.status_code == 200
    assert res_patch.json["predicted_milestone"] == 0
 
    res_del = client.delete(f"/growth-logs/{log_id}")
    assert res_del.status_code == 204

    res = client.get(f"/growth-logs/{log_id}")
    assert res.status_code == 404

# 13. Integration Test: plant check disease http metodu
def test_plant_check_disease_http(client):
    client.post('/users', json={'username': user_name, 'email': user_email, 'password': user_password})
    client.post("/plants", json={"name": "elma", "species": "apple", "user_id": 1})

    with patch("app.disease_model") as mock_model:
        mock_model.predict.return_value = [[0.72]]

        fake_file = (io.BytesIO(b"fake_image_data"), 'test.jpg')
        with patch('werkzeug.datastructures.FileStorage.save'), patch('PIL.Image.open'):
            res_post = client.post('/check-disease', data={
                'plant_id': 1,
                'file': fake_file
            })
    assert res_post.status_code == 201

    check_id = res_post.json['id']

    res_get = client.get(f"/disease-checks/{check_id}")
    assert res_get.status_code == 200
    assert res_get.json["confidence"] == 0.72

    res_patch = client.patch(f"/disease-checks/{check_id}", json={"disease_type_id": 4})
    assert res_patch.status_code in [200,400]
 
    res_del = client.delete(f"/disease-checks/{check_id}")
    assert res_del.status_code == 204

    res = client.get(f"/disease-checks/{check_id}")
    assert res.status_code == 404

# 14. Integration Test: plant care http metodu
def test_plant_care_http(client):
    client.post('/users', json={'username': user_name, 'email': user_email, 'password': user_password})
    plant = client.post("/plants", json={"name": "elma", "species": "apple", "user_id": 1})
    assert plant.status_code == 201

    plant_id = plant.json["id"]
  
    care = {
        "plant_id": plant_id,
        "medicine_name": "elma kullemesi",
        "notes": "gunde 2 kere verildi"
    }
    res_post = client.post('/plant-cares', json=care)
    assert res_post.status_code == 201

    care_id = res_post.json['id']

    res_get = client.get(f"/plant-cares/{care_id}")
    assert res_get.status_code == 200
    assert res_get.json["medicine_name"] == "elma kullemesi"

    res_patch = client.patch(f"/plant-cares/{care_id}", json={"notes": "gunde 1 kere verilmeye baslandi"})
    assert res_patch.status_code == 200

    res_del = client.delete(f"/plant-cares/{care_id}")
    assert res_del.status_code == 204

    res = client.get(f"/plant-cares/{care_id}")
    assert res.status_code == 404


