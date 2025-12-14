from flask import Flask
from flask_restx import Api, Resource

# Initialize Flask application
app = Flask(__name__)

# Swagger configuration
api = Api(app,
          version='1.0',
          title='Smart Plant Care API',
          description='Plant Care and Disease Detection API',
          doc='/docs'  # Swagger UI endpoint
          )

@api.route('/health')
class HealthCheck(Resource):
    def get(self):
        return {'status': "healthy"}, 200

if __name__ == '__main__':
    app.run(debug=True)
