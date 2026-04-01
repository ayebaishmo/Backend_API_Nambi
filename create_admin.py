from app import create_app
from extensions import db
from models.admin import Admin

app = create_app()
with app.app_context():
    # Delete all existing admins and start fresh
    Admin.query.delete()
    db.session.commit()

    admin = Admin(name='Tek Juice', position='Travel Manager')
    admin.set_password('tebuna')
    db.session.add(admin)
    db.session.commit()

    # Verify it was saved correctly
    check = Admin.query.filter_by(name='Tek Juice').first()
    if check and check.check_password('tebuna'):
        print("Admin created and verified successfully!")
        print(f"  ID:       {check.id}")
        print(f"  Name:     {check.name}")
        print(f"  Password: tebuna  (verified OK)")
    else:
        print("ERROR: Admin creation failed or password mismatch!")
