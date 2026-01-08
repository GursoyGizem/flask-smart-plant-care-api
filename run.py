from app import create_app
from app.extensions import db
from app.routes.disease_check import seed_disease_types
from datetime import datetime
import pandas as pd
import os
import warnings

app = create_app()

def parse_csv_date(date_str):
    if not date_str:
        return None
        
    formats = ["%Y-%m-%d", "%d/%m/%Y"] 
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt > datetime.now():
                warnings.warn(f"Future date detected: {date_str}", UserWarning)
            return dt
        except ValueError:
            continue
            
    return None 

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_disease_types()
    app.run(debug=True)

