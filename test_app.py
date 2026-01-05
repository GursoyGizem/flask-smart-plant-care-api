import pytest 
import io

from app import app, db, seed_disease_types
from unittest.mock import patch, MagicMock
from models import User, GrowthLog, DiseaseType

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

# 1. Senaryo: bir user nesnesi oluşturduğumda veriler doğru atanıyor mu?
def test_user_model_creation(client):
    user = User(username="gizem", email="gizem@gmail.com", password="nope")

    assert user.username == "gizem"
    assert user.email == "gizem@gmail.com"
    assert user.password == "nope"

# 2. Senaryo: User listesi çekildiğinde şifreler gizleniyor mu?
def test_user_hides_password(client):
    client.post("/users", json={
        "username": "gizem",
        "email": "gizem@gmail.com",
        "password": "gizli"
    })

    hides_user = client.get("/users")
    assert hides_user.status_code == 200

    data = hides_user.json
    assert "username" in data[0]
    assert "password" not in data[0]

# 3. Senaryo: aynı email adresiyle ikinci kez kayıt olunabiliyor mu?
def test_create_user_duplicate_email(client):
    user  = client.post('/users', json={
        "username": "gizem",
        "email": "gizem@example.com",
        "password": "ayni"
    })

    assert user.status_code == 201

    user_duplicate = client.post('/users', json={
        "username": "nur gizem",
        "email": "gizem@example.com",
        "password": "abcdef"
    })

    assert user_duplicate.status_code == 400
    assert "registered" in user_duplicate.json["message"]

# 4. Senaryo: bir user silindiginde ona ait olan bitkiler de otomatik siliniyor mu?
# create user -> create user's plant -> delete user -> research user's plant
def test_delete_user_cascades_plant(client):
    client.post('/users', json={
        "username": "gizem",
        "email": "gizem@example.com",
        "password": "ayni"
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

# 5. Senaryo: User bitki türlerini filtreleme yapabiliyor mu?
def test_user_plants_filter(client):
    client.post("/users", json={
        "username": "yaren",
        "email": "yareniko@example.com",
        "password": "ziraatmuh"
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

# 6. Senaryo: bir bitkiye ait bilgiler güncellenebiliyor mu?
def test_patch_plant(client):
    client.post("/users", json={
        "username": "mert",
        "email": "mert@hotmail.com",
        "password": "12345"
    })

    client.post("/plants", json={
        "name": "kaktus",
        "user_id": 1,
        "species": "san pedro cactus"
    })

    plant_update = client.patch("/plants/1", json = {"name": "ince uzun kaktus"})
    assert plant_update.status_code == 200
    assert plant_update.json["name"] == "ince uzun kaktus"
    assert plant_update.json["species"] == "san pedro cactus"

# 7. Senaryo: bir bitkiye ait growth logs dogru listeleniyor mu?
def test_plant_growth_history(client):
    client.post("/users", json={
        "username": "elife",
        "email": "elife@example.com",
        "password": "toprakanasi"
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

# 8. Senaryo: Plant Care History cekildiginde en son eklenen kayıt en uste geliyor mu?
def test_plant_care_history_sort(client):
    client.post("/users", json={
        "username": "farmer",
        "email": "farmer@example.com",
        "password": "toprakagasi"
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

# 9. Senaryo: model yuklenmemisse sistem hata veriyor mu?
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

# 10. Senaryo: kullanici growth log modeline gerekli bilgileri girmezse hata aliyor mu?
def test_predict_growth_null_fields(client):
    with patch("app.growth_model") as mock_model:
        with patch("app.model_columns", ["Soil_Type_Clay"]):
            client.post("/users", json={
                "username": "cavit",
                "email": "cavit@example.com",
                "password": "asdfgh"
            })

            client.post("/plants", json={
                "name": "salatalik",
                "user_id": 1
            })

            # temperature ve humidity yok
            plant_growth = client.post("/predict-growth", json = {
                "plant_id": 1,
                "soil_type": "Clay",
                "sunlight_hours": 6,
                "water_frequency": "Daily",
                "fertilizer_type": "None"
            })

            assert plant_growth.status_code == 400
            assert "errors" in plant_growth.json or "message" in plant_growth.json

# 11. Senaryo: disease plant modelinin gormedigi bir hastaligi kullanici vermek istediginde sistem hata veriyor mu?
@patch("app.disease_model")
def test_check_disease_unsupported_species(mock_model, client):
    with app.app_context():
        db.session.query(DiseaseType).delete()
        db.session.commit()
        seed_disease_types()

    client.post("/users", json={
        "username": "cicekci", 
        "email": "kaktus@test.com", 
        "password": "1"})
    
    client.post("/plants", json={
        "name": "Dikenli", 
        "species": "Kaktus", 
        "user_id": 1})

    fake_file = (io.BytesIO(b"data"), 'kaktus.jpg')

    with patch('werkzeug.datastructures.FileStorage.save'), patch('PIL.Image.open'):
        response = client.post('/check-disease', data={
            'plant_id': 1,
            'file': fake_file
        }, content_type='multipart/form-data')

    assert response.status_code == 400
    assert mock_model.predict.called == False

# 12. Senaryo: check disease modelinin threshold 0.5 kucukse model unknown olarak kaydediyor mu?
# predict = 0.3 -> confidence < 0.5 -> result: unknown disease
@patch("app.disease_model")
def test_check_disease_threshold(mock_model, client):
    mock_model.predict.return_value = [[0.3]]
    
    with app.app_context():
        seed_disease_types()

    client.post("/users", json={
        "username": "emircan",
        "email": "cancan@gmail.com",
        "password": "a1b2c1"
    })

    client.post("/plants", json={
        "name": "elma agaci",
        "species": "Apple",
        "user_id": 1
    })
    
    fake_file = (io.BytesIO(b"resim"), 'elma.jpg')
    with patch('werkzeug.datastructures.FileStorage.save'), patch('PIL.Image.open'):
        predict_threshold = client.post('/check-disease', data={
            'plant_id': 1,
            'file': fake_file
        }, content_type='multipart/form-data')

    assert predict_threshold.status_code == 201

    data = predict_threshold.json
    assert data["confidence"] == 0.3

# 13. Senaryo: check disease modele image yerine txt dosyası yüklenirse hata verir mi?
@patch('app.disease_model')
def test_check_disease_invalid_file_type(mock_model, client):
    with app.app_context():
        seed_disease_types()

    client.post("/users", json={
        "username": "gizem",
        "email": "gizem@example.com",
        "password": 1
        })

    client.post("/plants", json={
        "name": "Test",
        "species": "Apple",
        "user_id": 1
        })

    fake_txt = (io.BytesIO(b"Bu bir virus olabilir"), 'virus.txt')
    response = client.post('/check-disease', data={
        'plant_id': 1,
        'file': fake_txt
    }, content_type='multipart/form-data')

    assert response.status_code == 400

#14. Senaryo: Olmayan bir bitkiye bakım (Care) eklenmeye çalışılırsa 404 veriyor mu?
def test_add_care_none_plant(client):
    response = client.post('/plant-cares', json={
        "plant_id": 9, 
        "medicine_name": "İlaç",
        "notes": "Hata testi"
    })

    assert response.status_code == 404
    assert "plant not found" in response.json['message']

# 15. Senaryo: Büyüme tahmini (Growth Predict) başarılı olduğunda veritabanına kaydediyor mu?
def test_predict_growth_success(client):
    client.post("/users", json={
        "username": "gizem", 
        "email": "gizem@example.com", 
        "password": "1"})
    client.post("/plants", json={
        "name": "biber", 
        "species": "pepper",
        "user_id": 1})

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

            response = client.post("/predict-growth", json=input_data)

            assert response.status_code == 200
            
            logs = client.get("/plants/1/growth-logs")
            data = logs.json
            
            assert len(data) == 1
            assert data[0]['predicted_milestone'] == 1