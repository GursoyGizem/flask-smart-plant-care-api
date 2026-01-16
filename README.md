<div align="center">

[![CI/CD ve Test Otomasyonu](https://github.com/GursoyGizem/flask-smart-plant-care-api/actions/workflows/ci_cd_pipeline.yml/badge.svg)](https://github.com/GursoyGizem/flask-smart-plant-care-api/actions/workflows/ci_cd_pipeline.yml)
[![codecov](https://codecov.io/gh/GursoyGizem/flask-smart-plant-care-api/graph/badge.svg)](https://codecov.io/gh/GursoyGizem/flask-smart-plant-care-api)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat&logo=python&logoColor=white)

<br>

![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![Flask-RESTX](https://img.shields.io/badge/Flask--RESTX-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-%23D71F00.svg?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)
![Pytest](https://img.shields.io/badge/pytest-%230A9EDC.svg?style=for-the-badge&logo=pytest&logoColor=white)

<br>

![TensorFlow](https://img.shields.io/badge/TensorFlow-%23FF6F00.svg?style=for-the-badge&logo=TensorFlow&logoColor=white)
![Keras](https://img.shields.io/badge/Keras-%23D00000.svg?style=for-the-badge&logo=Keras&logoColor=white)
![Scikit-Learn](https://img.shields.io/badge/scikit--learn-%23F7931E.svg?style=for-the-badge&logo=scikit-learn&logoColor=white)

<br>

![NumPy](https://img.shields.io/badge/numpy-%23013243.svg?style=for-the-badge&logo=numpy&logoColor=white)
![Pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-%233776AB.svg?style=for-the-badge&logo=python&logoColor=white)

</div>

---
 
# flask-smart-plant-care-api
FSmart Plant Care API, ML tabanlı yöntemler kullanarak bitkilerde görülen hastalıkların otomatik olarak tespit edilmesini ve bitki büyüme süreçlerinin tahmin edilmesini amaçlamaktadır. API, bitki takibi, hastalık analizi ve büyüme tahmini işlevlerini sağlayan RESTful API'dir.

### Temel Özellikler

- **Kullanıcı Yönetimi**: Kullanıcı kaydı ve yönetimi
- **Bitki Takibi**: Birden fazla bitki ekleme ve yönetme
- **Hastalık Tespiti**: Bitki görüntülerinden AI tabanlı hastalık tespiti
- **Büyüme Tahmini**: Çevresel faktörlere göre bitki büyüme tahmini
- **Tedavi Takibi**: Uygulanan tedavilerin kayıt altına alınması
  
##  Kurulum Talimatları

### Gereksinimler
- Python 3.10+
- pip 

#### Adım 1: Projeyi Klonlayın
`git clone https://github.com/GursoyGizem/flask-smart-plant-care-api.git`

`cd flask-smart-plant-care-api`

#### Adım 2: Virtual Environment Oluşturun
`python -m venv venv`

`venv\Scripts\activate`

#### Adım 3: Bağımlılıkları Yükleyin
`pip install -r requirements.txt`

## Uygulamayı Çalıştırma

**Geliştirme Sunucusunu Başlatın:** `python run.py`. Uygulama varsayılan olarak `http://localhost:5000` adresinde çalışacaktır.

**API Dokümantasyonuna Erişim**: Swagger UI dokümantasyonu şu adreste mevcuttur: `http://localhost:5000/docs`

## API Endpoint'lerinin Listesi
###  Kullanıcı İşlemleri
- `GET /users` - Tüm kullanıcıları listele
- `POST /users` - Yeni kullanıcı oluştur
- `DELETE /users/{id}` - Kullanıcıyı sil
- `GET /users/{id}` - Kullanıcı detaylarını getir
- `PATCH /users/{id}` - Kullanıcı bilgilerini güncelle

#### Kullanım Örneği: Yeni kullanıcı oluşturma
**Request**
```json 
{
  "username": "gizem",
  "email": "gizem@example.com",
  "password": "Password123!"
}
```

**Response**
```json 
{
  "id": 1,
  "username": "gizem",
  "email": "gizem@example.com",
}
```

### Bitki İşlemleri
- `GET /plants` - Tüm bitkileri listele
- `POST /plants` - Yeni bitki ekle
- `DELETE /plants/{id}` - Bitkiyi sil
- `GET /plants/{id}` - Bitki detaylarını getir
- `PATCH /plants/{id}` - Bitki bilgilerini güncelle
- `GET /users/{user_id}/plants` - Kullanıcının bitkilerini listele 

#### Kullanım Örneği: Bitki ekleme
**Request**
```json 
{
  "name": "Arka Bahçe Elma",
  "species": "Apple",
  "user_id": 1
}
```

**Response**
```json 
{
  "id": 5,
  "name": "Arka Bahçe Elma",
  "species": "Apple",
  "user_id": 1
}
```

### Büyüme Tahmini
- `GET /growth-logs` - Tüm büyüme kayıtlarını listele
- `DELETE /growth-logs/{id}` - Büyüme kaydını sil
- `GET /growth-logs/{id}` - Büyüme kaydı detaylarını getir
- `PATCH /growth-logs/{id}` - Büyüme kaydını güncelle
- `GET /plants/{plant_id}/growth-logs` - Bitkinin büyüme geçmişini listele
- `POST /predict-growth` - Bitki büyüme tahmini yap

#### Kullanım Örneği: Büyüme tahmini
**Request**
```json 
{
  "plant_id": 1,
  "soil_type": "Clay",
  "sunlight_hours": 7.5,
  "water_frequency": "Daily",
  "fertilizer_type": "Nitrogen",
  "temperature": 24.0,
  "humidity": 55.0
}
```

**Response**
```json 
{
  "id": 42,
  "plant_id": 1,
  "date": "2026-01-16T23:00:00",
  "predicted_milestone": 1,
  "soil_type": "Clay",
  "sunlight_hours": 7.5,
  "water_frequency": "Daily",
  "fertilizer_type": "Nitrogen",
  "temperature": 24.0,
  "humidity": 55.0
}
```

### Hastalık Tespiti
- `POST /check-disease` - Hastalık tespiti yap (görüntü yükleme)
- `GET /disease-checks` - Tüm hastalık kontrollerini listele
- `DELETE /disease-checks/{id}` - Hastalık kontrolünü sil
- `GET /disease-checks/{id}` - Hastalık kontrolü detaylarını getir
- `PATCH /disease-checks/{id}` - Hastalık kontrolünü güncelle
- `GET /plants/{plant_id}/disease-checks` - Bitkinin hastalık geçmişini listele
- `GET /disease-type` - Desteklenen hastalık türlerini listele

#### Kullanım Örneği: Hastalık tespiti
**İstek (Request):**
* `plant_id`: 1
* `file`: apple.jpg

**Response**
```json 
{
  "id": 12,
  "plant_id": 1,
  "disease_name": "Apple Black Rot",
  "confidence": 0.95,
  "image_url": "/static/uploads/leaves/prediction_12.jpg",
  "created_at": "2024-01-16T14:20:00"
}
```

### Tedavi Takibi
- `GET /plant-cares` - Tüm tedavi kayıtlarını listele
- `POST /plant-cares` - Yeni tedavi kaydı ekle
- `DELETE /plant-cares/{id}` - Tedavi kaydını sil
- `GET /plant-cares/{id}` - Tedavi kaydı detaylarını getir
- `PATCH /plant-cares/{id}` - Tedavi kaydını güncelle
- `GET /plants/{plant_id}/cares` - Bitkinin tedavi geçmişini listele

#### Kullanım Örneği: Tedavi güncelleme 
```json 
{
  "notes": "Tedavi sabah akşam uygulandı."
}
```

**Response**
```json 
{
  "id": 8,
  "plant_id": 1,
  "disease_check_id": 12,
  "medicine_name": "Mantar Önleyici Sprey",
  "application_date": "2024-01-16T12:05:00",
  "notes": "Tedavi sabah akşam uygulandı."
}
```

## Test Çalıştırma Komutları

**Tüm testleri çalıştırmak için:** `pytest -m pytest`

**Belirli bir testi çalıştırmak için:** `python -m pytest tests/test_system.py::test_system_disease_progression`

**Belirli dosyadaki tüm testleri çalıştırmak için:** `python -m pytest tests/test_system.py`

**Kod kapsama raporu oluşturmak için:** `python -m pytest --cov=app --cov-report=html`

HTML raporu `htmlcov/index.html` dosyasında görüntülenebilir.

### Test Kategorileri
- **Unit Testler (15 adet)**: Fonksiyonlar ve modeller
- **Integration Testler (14 adet)**: API endpoint'leri ve veritabanı işlemleri
- **System Testler (7 adet)**: End-to-end senaryolar

