from flask_sqlalchemy import SQLAlchemy
import uuid

db = SQLAlchemy()

class Guest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    montant_attendu = db.Column(db.Integer, nullable=False)
    devise = db.Column(db.String(10), nullable=False, default='USD')
    code_unique = db.Column(db.String(50), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    essais_echoues = db.Column(db.Integer, default=0, nullable=False)
    a_paye = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<Guest {self.nom}>"
