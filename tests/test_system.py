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

# 5. System Test: kullanici hesabini sildiginde, ona ait bitkiler, bakim kayitlari ve analizleri de silinme kontrolu
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

# 6. System Test: Kullanici birden fazla bitki icin hastalik taramasi yapar, hastalikli bilgiye tedavi uygular ve saglikli bitkinin buyume takibi yapilir
"""
1. Kullanici sisteme kayit olur
2. 2 tane bitki kaydi olusturur
3. Birinci bitkinin hastalik taramasi yapilir ve yuksek confidence ile hastalik tespit edilir
4. İkinci bitkinin hastalik taramasi yapilir ve dusuk confidence ile saglikli sonucu alinir
5. Birinci bitkiye tedavi uygulanir
6. İkinci bitkinin buyume verisi girilir ve tahmin yapilir
6. Bitki kayitlarinin gecmisleri kontrol edilir
"""
def test_multi_plant_management(client):
    client.post('/users', json={'username': user_name, 'email': user_email, 'password': user_password})
    plant1 = client.post("/plants", json={"name": "red apple", "species":"apple", "user_id": 1}).json["id"]
    plant2 = client.post("/plants", json={"name": "green apple", "species":"apple", "user_id": 1}).json["id"]

    with patch('app.extensions.disease_model') as mock_disease_model:
        mock_disease_model.predict.return_value = [[0.95]]
        fake_file1 = (io.BytesIO(b"fake_r_apple_img"), "r_apple.jpg")

        with patch("werkzeug.datastructures.FileStorage.save"), patch("PIL.Image.open"):
            unhealthy_plant = {"plant_id": plant1, "file": fake_file1}
            check1 = client.post("/check-disease", data=unhealthy_plant)

            assert check1.status_code == 201
            assert check1.json["confidence"] > 0.90

        mock_disease_model.predict.return_value = [[0.2]]
        fake_file2 = (io.BytesIO(b"fake_g_apple_img"), "g_apple.jpg")

        with patch("werkzeug.datastructures.FileStorage.save"), patch("PIL.Image.open"):
            healthy_plant = {"plant_id": plant2, "file": fake_file2}
            check2 = client.post("/check-disease", data=healthy_plant)

            assert check2.status_code == 201

    care = client.post("/plant-cares", json={
        "plant_id": plant1,
        "medicine_name": "yanik spreyi",
        "notes": "agac dibine uygulandi",
        "disease_check_id": check1.json.get('id')
    })

    assert care.status_code == 201
    
    with patch("app.extensions.growth_model") as mock_model:
        mock_model.predict.return_value = [3] 

        input_data = {
            "plant_id": plant2,
            "soil_type": "Loam",
            "sunlight_hours": 6.5,
            "water_frequency": "Daily",
            "fertilizer_type": "Nitrogen",
            "temperature": 24.0,
            "humidity": 55.0
            }
        
        fake_columns = ["Soil_Type_Clay", "Water_Frequency_Daily", "Temperature", "Humidity", "Sunlight_Hours", "Fertilizer_Type_None"]
        with patch("app.extensions.model_columns", fake_columns):
            res = client.post('/predict-growth', json=input_data)
            assert res.status_code == 200

    cares = client.get('/plant-cares')
    assert len(cares.json) >= 1

# 7. System Test: Kullanici ayni bitki icin hastalik taramasi yapar ve tedavi takibi gerceklesir
"""
1. Kullanici sisteme kayit olur ve bitki ekler
2. Bitkiye hastalik taramasi yapilir birinci sonuc high confidence cikar
3. Tedavi uygulanir
3. Bitkiye 1 hafta sonra hastalik taramasi yapilir  ikinci sonuc medium confidence cikar
4. Tedavi uygulanir
5. Bitkiye 2 hafta sonra hastalik taramasi yapilir ucuncu sonuc low confidence cikar
6. Bitkinin hastalik ve tedavi gecmisi listelenir
"""
def test_system_disease_progression(client):
    client.post('/users', json={'username': user_name, 'email': user_email, 'password': user_password})
    plant_id = client.post("/plants", json={"name": "red apple", "species": "apple", "user_id": 1}).json["id"]

    with patch("app.extensions.disease_model") as mock_disease_model:
        mock_disease_model.predict.return_value = [[0.95]]
        fake_file1 = (io.BytesIO(b"fake_img"), "apple.jpg")

        with patch("werkzeug.datastructures.FileStorage.save"), patch("PIL.Image.open"):
            check1 = client.post("/check-disease", data={"plant_id": plant_id, "file": fake_file1})

            assert check1.status_code == 201
            assert check1.json["confidence"] > 0.90
            
            client.post("/plant-cares", json={
                "plant_id": plant_id, 
                "medicine_name": "2 doz bakteri", 
                "disease_check_id": check1.json['id']
            })

        mock_disease_model.predict.return_value = [[0.62]]
        fake_file2 = (io.BytesIO(b"fake_img"), "apple.jpg")

        with patch("werkzeug.datastructures.FileStorage.save"), patch("PIL.Image.open"):
            check2 = client.post("/check-disease", data={"plant_id": plant_id, "file": fake_file2})

            assert check2.status_code == 201
            assert 0.50 < check2.json["confidence"] < 0.80

            client.post("/plant-cares", json={
                "plant_id": plant_id, 
                "medicine_name": "1 doz bakteri", 
                "disease_check_id": check2.json['id']
            })

        mock_disease_model.predict.return_value = [[0.32]]
        fake_file3 = (io.BytesIO(b"fake_img"), "appleclea.jpg")

        with patch("werkzeug.datastructures.FileStorage.save"), patch("PIL.Image.open"):
            check3 = client.post("/check-disease", data={"plant_id": plant_id, "file": fake_file3})
            assert check3.status_code == 201
            assert check3.json["confidence"] < 0.50

    history = client.get(f"/plants/{plant_id}/cares").json
    assert len(history) == 2 