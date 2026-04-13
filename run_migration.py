from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE fabric_roll ADD COLUMN location VARCHAR(100) DEFAULT 'Almacén de Telas'"))
        db.session.commit()
        print("Agregada columna location")
    except Exception as e:
        db.session.rollback()
        print("La columna location quizás ya existe:", e)
        
    try:
        db.session.execute(text("ALTER TABLE fabric_roll ADD COLUMN provisioned_by_client VARCHAR(200)"))
        db.session.commit()
        print("Agregada columna provisioned_by_client")
    except Exception as e:
        db.session.rollback()
        print("La columna provisioned_by_client quizás ya existe:", e)
