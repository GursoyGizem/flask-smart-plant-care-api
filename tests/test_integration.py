import pytest 
import io
import pandas as pd 
import time

from app.extensions import db
from unittest.mock import patch
from app.routes.disease_check import seed_disease_types
from app.models import GrowthLog, DiseaseType

user_name = "gizem"
user_email = "gizem@example.com"
user_password = "Gizem.123"

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
def test_plant_growth_history(client, app):
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

    time.sleep(1)
    
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

    with patch("app.extensions.growth_model", None):
        response1 = client.post("/predict-growth", json = input_data)
        assert response1.status_code == 503

    with patch("app.extensions.disease_model", None):
        response2 = client.post("/check-disease", json = {"plant_id": 1})
        assert response2.status_code == 503

# 8. Intregration Test: disease plant modelinin gormedigi bir hastaligi kullanici vermek istediginde sistem hata veriyor mu?
@patch("app.extensions.disease_model")
def test_check_disease_unsupported_species(mock_model, client, app):
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

    with patch("app.extensions.growth_model") as mock_model:
        mock_model.predict.return_value = [1] 
        with patch("app.extensions.model_columns", ["Soil_Type_Clay", "Water_Frequency_Daily"]):
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

    with patch("app.extensions.disease_model") as mock_model:
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
