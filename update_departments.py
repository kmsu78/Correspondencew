from flask import Flask
import os
import sqlite3

# إنشاء تطبيق Flask مؤقت للوصول إلى إعدادات قاعدة البيانات
app = Flask(__name__, instance_relative_config=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'correspondence.db')

def update_database():
    """تحديث قاعدة البيانات لإضافة جدول الأقسام وتحديث جدول المستخدمين"""
    try:
        # الحصول على مسار قاعدة البيانات
        db_path = os.path.join(app.instance_path, 'correspondence.db')
        
        # التحقق من وجود قاعدة البيانات
        if not os.path.exists(db_path):
            print(f"قاعدة البيانات غير موجودة في المسار: {db_path}")
            return False
        
        # إنشاء اتصال بقاعدة البيانات
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. إنشاء جدول الأقسام إذا لم يكن موجودًا
        print("التحقق من وجود جدول department...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='department'")
        if not cursor.fetchone():
            print("إنشاء جدول department...")
            cursor.execute("""
                CREATE TABLE department (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            print("تم إنشاء جدول department بنجاح!")
            
            # إضافة بعض الأقسام الافتراضية
            print("إضافة أقسام افتراضية...")
            default_departments = [
                ('الإدارة', 'قسم الإدارة العامة'),
                ('تكنولوجيا المعلومات', 'قسم تكنولوجيا المعلومات'),
                ('الموارد البشرية', 'قسم الموارد البشرية'),
                ('المالية', 'قسم المالية والمحاسبة'),
                ('خدمة العملاء', 'قسم خدمة العملاء')
            ]
            
            cursor.executemany(
                "INSERT INTO department (name, description) VALUES (?, ?)",
                default_departments
            )
            print("تم إضافة الأقسام الافتراضية بنجاح!")
        else:
            print("جدول department موجود بالفعل")
        
        # 2. تحديث جدول المستخدمين لإضافة حقل department_id
        print("التحقق من وجود حقل department_id في جدول user...")
        cursor.execute("PRAGMA table_info(user)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'department_id' not in column_names:
            print("إضافة حقل department_id إلى جدول user...")
            cursor.execute("ALTER TABLE user ADD COLUMN department_id INTEGER REFERENCES department(id)")
            print("تم إضافة حقل department_id بنجاح!")
            
            # إضافة حقل department_name للتوافق مع الإصدارات السابقة
            if 'department_name' not in column_names:
                print("إضافة حقل department_name إلى جدول user...")
                cursor.execute("ALTER TABLE user ADD COLUMN department_name VARCHAR(80)")
                print("تم إضافة حقل department_name بنجاح!")
            
            # تحديث department_id بناءً على department الحالي
            print("تحديث department_id للمستخدمين الحاليين...")
            
            # الحصول على قائمة المستخدمين وأقسامهم
            cursor.execute("SELECT id, department FROM user WHERE department IS NOT NULL")
            users = cursor.fetchall()
            
            # تحديث department_id لكل مستخدم
            for user_id, department_name in users:
                # البحث عن القسم المطابق
                cursor.execute("SELECT id FROM department WHERE name = ?", (department_name,))
                department = cursor.fetchone()
                
                if department:
                    # تحديث department_id
                    cursor.execute("UPDATE user SET department_id = ?, department_name = ? WHERE id = ?", 
                                  (department[0], department_name, user_id))
                    print(f"تم تحديث department_id للمستخدم {user_id}")
                else:
                    # إنشاء قسم جديد إذا لم يكن موجودًا
                    cursor.execute("INSERT INTO department (name, description) VALUES (?, ?)", 
                                  (department_name, f"قسم {department_name}"))
                    department_id = cursor.lastrowid
                    
                    # تحديث department_id
                    cursor.execute("UPDATE user SET department_id = ?, department_name = ? WHERE id = ?", 
                                  (department_id, department_name, user_id))
                    print(f"تم إنشاء قسم جديد وتحديث department_id للمستخدم {user_id}")
        else:
            print("حقل department_id موجود بالفعل في جدول user")
        
        # حفظ التغييرات
        conn.commit()
        print("تم تحديث قاعدة البيانات بنجاح!")
        
        # إغلاق الاتصال
        conn.close()
        return True
        
    except Exception as e:
        print(f"حدث خطأ أثناء تحديث قاعدة البيانات: {str(e)}")
        return False

# تشغيل وظيفة تحديث قاعدة البيانات
if __name__ == "__main__":
    # التأكد من وجود مجلد instance
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # تحديث قاعدة البيانات
    if update_database():
        print("تم تحديث قاعدة البيانات بنجاح!")
    else:
        print("فشل تحديث قاعدة البيانات.")
