import pytest 
import io
import pandas as pd 
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from PIL import Image

from app.extensions import db
from app.models import User, Plant, GrowthLog, DiseaseType, PlantCare

from app.routes.user import validate_email_format, validate_password_strength 
from app.routes.disease_check import seed_disease_types, format_disease_name, predict_disease, validate_image_format
from app.routes.growth_log import prepare_prediction_dataframe

user_name = "gizem"
user_email = "gizem@example.com"
user_password = "Gizem.123"

# 1. System Test: kullanici sisteme kaydolur, bitki ekler, hastalik taramasi yapar ve buna uygun tedavi ekler
"""
Adimlar:
1. Kullanici kayit olusturur (post/users)
2. Kullanici sisteme bitki ekler (post/plants)
3. Kullanici ayni bitkiye  gecerli bir resim yukler ve hastalik taramasi yapar (post/check-disease)
4. Sistemden hastalik tahmin sonucu donmesi beklenir
5. Donen hastalik sonucuna gore bitkiye tedavi notu eklenir (post/plant-cares)
6. Bitkinin bakim gecmisi cekilir ve eklenen notun orada oldugu dogrulanir (/plants/{plants_id}/cares)
"""
def test_full_system_care(client, app):
    client.post('/users', json={'username': user_name, 'email': user_email, 'password': user_password})
    plant = client.post("/plants", json={"name": "apple black disease", "species": "apple", "user_id": 1})
    plant_id = plant.json["id"]

    with patch("app.extensions.disease_model") as mock_model:
        mock_model.predict.return_value = [[0.83]]

        fake_file = (io.BytesIO(b"fake_leaf_img"), "leaf.jpg")
        with patch("werkzeug.datastructures.FileStorage.save"), patch("PIL.Image.open"):
            check_res = client.post("/check-disease", data={"plant_id": plant_id, "file": fake_file})
            assert check_res.status_code == 201

    care = {
        "plant_id": plant_id,
        "medicine_name": "apple black treatment",
        "notes": "birinci agaca uygulandi"
    }
    client.post("/plant-cares", json=care)

    history = client.get(f"/plants/{plant_id}/cares").json
    assert history[0]["medicine_name"] ==  "apple black treatment"


# 2. System Test: kullanici bitki bilgilerini yanlis girmesi durumunda guncelleme yapabilmesi ve bitki oldugunde sistemden siebilmesi
"""
Adimlar:
1. Kullanici kayit olusturur (post/users)
2. Kullanici sisteme bitki ekler (post/plants)
3. Kullanici plant sayfasinda bitki detaylarini goruntuler (get/plants/{id})
4. Bitki ismi ve species guncellenir (patch/plants/{id})
5. Bitki detaylarinin degistigi dogrulanir (get/plants/{id})
6. Bitki silinir (delete/plants)
8. Silinen bitkiye erisilmedigi dogrulanir (get -> 404)
"""
def test_system_crud(client):
    # Kullanici kayit olusturur ve bitki ekler
    client.post('/users', json={'username': user_name, 'email': user_email, 'password': user_password})
    plant = client.post("/plants", json={"name": "blueberry", "species": "vegetable", "user_id": 1})
    plant_id = plant.json["id"]

    # Kullanici plant sayfasinda bitki detaylarini goruntuler
    assert client.get(f"/plants/{plant_id}").json["name"] == "blueberry"

    # Bitki ismi ve species guncellenir 
    client.patch(f"/plants/{plant_id}", json ={"name":"strawberry", "species":"fruit"})
    assert client.get(f"/plants/{plant_id}").json["name"] == "strawberry" and client.get(f"/plants/{plant_id}").json["species"] == "fruit"

    # Bitki silinir 
    client.delete(f"/plants/{plant_id}")

    #Silinen bitkiye erisilmedigi dogrulanir 
    assert client.get(f"/plants/{plant_id}").status_code == 404

# 3. System Test: kullanicinin bitki buyume verilerini girerken sistemin tahmin uretmesi ve gecmis buyume verilerini listeleyebilmesi
"""
Adimlar:
1. Kullanici bitki olusturur (post/plants)
2. Kullanici buyume verilerini girer 
3. Mock model calisir
4. Sistem model sonucunu dondurdugu dogrulanir 
6. Bitkinin tum growth log listesi cekilir ve kaydin veritabanina islendigi dogrulanir (/plants/{id}/growth-logs)
"""
def test_system_growth_prediction(client):
    # Kullanici kayit olusturur ve bitki ekler
    client.post('/users', json={'username': user_name, 'email': user_email, 'password': user_password})
    plant = client.post("/plants", json={"name": "blueberry", "species": "vegetable", "user_id": 1})
    plant_id = plant.json["id"]

    input_data = {
                "plant_id": 1,
                "soil_type": "Clay",
                "sunlight_hours": 8.0,
                "water_frequency": "Daily",
                "fertilizer_type": "None",
                "temperature": 25.0,
                "humidity": 60.0
            }
    
    # Kullanici buyume verilerini girer ve model calisir
    with patch("app.extensions.growth_model") as mock_model:
        mock_model.predict.return_value = [1] 
        fake_columns = ["Soil_Type_Clay", "Water_Frequency_Daily", "Temperature", "Humidity", "Sunlight_Hours", "Fertilizer_Type_None"]
        with patch("app.extensions.model_columns", fake_columns):
            #Sistem model sonucunu dondurdugu dogrulanir 
            res = client.post('/predict-growth', json=input_data)
            assert res.status_code == 200

    # Bitkinin tum growth log listesi cekilir ve kaydin veritabanina islendigi dogrulanir 
    logs = client.get(f'/plants/{plant_id}/growth-logs').json
    assert len(logs) == 1
    assert logs[0]['predicted_milestone'] == 1

# 4. System Test: user A'nin bilgilerini user B'nin goremedigi veya degistiremedigini dogrulayan guvenlik senaryosu
"""
Adimlar:
1. User A ve User B olusturulur
2. User A ve B bitki ekler
3. User B bitki listesini ceker (/users/{id}/plants)
4. User B'nin bitki listesinde user A'nin bitkilerini icermedigi dogrulanir
"""
def test_system_user_security(client):
    # User A ve User B olusturulur
    client.post('/users', json={'username': "user_a", 'email': "user_a@gmail.com", 'password': "User*a123!"})
    b_id = client.post('/users', json={'username': "user_b", 'email': "user_b@gmail.com", 'password': "User*b123!"}).json["id"]

    # User A ve B bitki ekler
    client.post("/plants", json={"name": "user's a plant", "user_id": 1})
    client.post("/plants", json={"name": "user's b plant", "user_id": 2})

    # User B bitki listesini ceker
    res = client.get(f"/users/{b_id}/plants")
    assert res.status_code == 200
    
    plant_b = res.json

    # User B'nin bitki listesinde user A'nin bitkilerini icermedigi dogrulanir
    plant_names = [p["name"] for p in plant_b]
    assert "users a plant" not in plant_names

# 5. System Test: kullanici hesabini sildiginde, ona ait bitkiler, bakim kayitlari ve analizleri de silinme kontrolü
"""
Adimlar:
1. Kullanici olusturulur, bitki ve tedavi eklenir
2. Kullanici hesabini siler
3. Bitki ID'si ile sorgu yapilir ve hata alinmasi beklenir
4. Plant ID'si ile sorgu yapilir ve hata alinmasi beklenir
"""
def test_system_cascade_delete(client):
    # Kullanici olusturulur, bitki ve tedavi eklenir
    user_id = client.post('/users', json={'username': user_name, 'email': user_email, 'password': user_password}).json["id"]
    plant_id = client.post("/plants", json={"name": "plant", "user_id": 1}).json["id"]
    care_id = client.post("/plant-cares", json={"plant_id": plant_id, "medicine_name": "medicine", "notes": "gunde 2 kere"}).json['id']

    # Kullanici hesabini siler
    client.delete(f'/users/{user_id}')
   
    # Bitki ID'si ile sorgu yapilir ve hata alinmasi beklenir
    assert client.get(f'/plants/{plant_id}').status_code == 404

    # Plant ID'si ile sorgu yapilir ve hata alinmasi beklenir
    assert client.get(f'/plant-cares/{care_id}').status_code == 404