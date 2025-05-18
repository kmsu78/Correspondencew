from app import app, db, User
from werkzeug.security import generate_password_hash

def recreate_db():
    with app.app_context():
        # Drop all tables
        db.drop_all()

        # Create all tables with new schema
        db.create_all()

        # Create admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            department='IT',
            role='admin',
            is_active=True,
            # إضافة الحقول الجديدة
            full_name='مدير النظام',
            phone='0123456789',
            position='مدير النظام',
            bio='حساب مدير النظام الرئيسي',
            profile_image='/static/img/profile/default.png',
            theme='light',
            language='ar',
            notifications_enabled=True
        )
        admin.password = generate_password_hash('admin123')

        db.session.add(admin)
        db.session.commit()
        print('Database recreated and admin user created successfully!')

if __name__ == '__main__':
    recreate_db()
