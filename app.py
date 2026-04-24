from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from models import db, Guest
import qrcode
import io
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///birthday.db'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-very-secret')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Pakas')

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    guests = Guest.query.order_by(Guest.id.desc()).all()
    return render_template('index.html', guests=guests)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin'))
        else:
            flash('Mot de passe incorrect', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin'):
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        nom = request.form.get('nom')
        montant = request.form.get('montant')
        devise = request.form.get('devise', 'USD')
        if nom and montant:
            new_guest = Guest(nom=nom.strip(), montant_attendu=int(montant), devise=devise)
            db.session.add(new_guest)
            db.session.commit()
            flash(f'Invité {nom} ajouté avec succès !', 'success')
            return redirect(url_for('admin'))
    
    guests = Guest.query.order_by(Guest.id.desc()).all()
    return render_template('dashboard.html', guests=guests)

@app.route('/admin/reset/<int:guest_id>', methods=['POST'])
def reset_guest(guest_id):
    if not session.get('admin'): return redirect(url_for('login'))
    guest = Guest.query.get_or_404(guest_id)
    guest.essais_echoues = 0
    guest.a_paye = False
    db.session.commit()
    flash(f"L'invité {guest.nom} a été réinitialisé.", 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:guest_id>', methods=['POST'])
def delete_guest(guest_id):
    if not session.get('admin'): return redirect(url_for('login'))
    guest = Guest.query.get_or_404(guest_id)
    db.session.delete(guest)
    db.session.commit()
    flash(f'Invité supprimé.', 'warning')
    return redirect(url_for('admin'))

@app.route('/qr/<code_unique>')
def generate_qr(code_unique):
    guest = Guest.query.filter_by(code_unique=code_unique).first_or_404()
    verify_url = request.url_root + 'verify/' + code_unique
    
    # Generate QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

@app.route('/invitation/<code_unique>')
def invitation(code_unique):
    guest = Guest.query.filter_by(code_unique=code_unique).first_or_404()
    # On génère l'URL complète pour que l'invité puisse savoir où il va
    return render_template('invitation.html', guest=guest)

@app.route('/scan')
def scan():
    if not session.get('admin'): return redirect(url_for('login'))
    return render_template('scanner.html')

@app.route('/verify/<code_unique>', methods=['GET', 'POST'])
def verify(code_unique):
    if not session.get('admin'): return redirect(url_for('login'))
    guest = Guest.query.filter_by(code_unique=code_unique).first_or_404()
    
    if request.method == 'POST':
        # Si la personne est déjà bloquée
        if guest.essais_echoues >= 2:
            return render_template('verify.html', guest=guest, error="Ah papa !! Olekisi", locked=True)
        
        # Saisies
        nom_saisi = request.form.get('nom', '').strip()
        montant_saisi = request.form.get('montant', '0').strip()
        
        try:
            montant_saisi = int(montant_saisi)
        except ValueError:
            montant_saisi = -1 # invalide
            
        # Vérification nom & montant
        # On va rendre la vérification du nom insensible à la casse
        if nom_saisi.lower() == guest.nom.lower() and montant_saisi == guest.montant_attendu:
            guest.a_paye = True
            db.session.commit()
            flash(f"ENTRÉE VALIDÉE : Bienvenue {guest.nom} ! ✅", "success")
            return redirect(url_for('index'))
        else:
            # Erreur !
            guest.essais_echoues += 1
            db.session.commit()
            
            if guest.essais_echoues == 1:
                return render_template('verify.html', guest=guest, error="Tala muyibi oyo")
            else:
                return render_template('verify.html', guest=guest, error="Ah papa !! Olekisi", locked=True)
            
    return render_template('verify.html', guest=guest)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
