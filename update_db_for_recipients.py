import os
import sqlite3
import traceback
from app import app, db, User, UserGroup, UserGroupMembership, FavoriteUser, MessageRecipient, Message
from datetime import datetime

# تفعيل وضع التصحيح
DEBUG = True

def debug_print(message):
    """طباعة رسالة تصحيح إذا كان وضع التصحيح مفعلاً"""
    if DEBUG:
        print(f"[DEBUG] {message}")

def find_database_file():
    """البحث عن ملف قاعدة البيانات في المجلدات المحتملة"""
    # المسارات المحتملة لقاعدة البيانات
    possible_paths = [
        os.path.join(app.instance_path, 'app.db'),
        os.path.join(os.getcwd(), 'app.db'),
        os.path.join(os.getcwd(), 'instance', 'app.db'),
        os.path.join(app.instance_path, 'correspondence.db'),
        os.path.join(os.getcwd(), 'correspondence.db'),
        os.path.join(os.getcwd(), 'instance', 'correspondence.db')
    ]

    # البحث عن أي ملف .db في المجلد الحالي
    db_files = [f for f in os.listdir('.') if f.endswith('.db')]
    for db_file in db_files:
        possible_paths.append(os.path.join(os.getcwd(), db_file))

    # البحث عن أي ملف .db في مجلد instance
    if os.path.exists('instance'):
        instance_db_files = [f for f in os.listdir('instance') if f.endswith('.db')]
        for db_file in instance_db_files:
            possible_paths.append(os.path.join(os.getcwd(), 'instance', db_file))

    # التحقق من وجود الملفات
    for path in possible_paths:
        if os.path.exists(path):
            print(f"تم العثور على قاعدة البيانات في: {path}")
            return path

    return None

def update_database_schema():
    """تحديث هيكل قاعدة البيانات لدعم المستلمين المتعددين"""
    print("جاري تحديث هيكل قاعدة البيانات...")

    try:
        # التحقق من وجود الجداول الجديدة
        debug_print("التحقق من وجود الجداول الجديدة...")
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        debug_print(f"الجداول الموجودة: {existing_tables}")

        # إضافة الأعمدة الجديدة إلى جدول الرسائل
        debug_print("جاري إضافة الأعمدة الجديدة إلى جدول الرسائل...")

        # الحصول على مسار قاعدة البيانات
        db_path = find_database_file()
        if not db_path:
            print("لم يتم العثور على قاعدة البيانات")
            return False

        # الاتصال بقاعدة البيانات
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # التحقق من وجود الأعمدة الجديدة
        cursor.execute("PRAGMA table_info(message)")
        columns = [column[1] for column in cursor.fetchall()]
        debug_print(f"الأعمدة الموجودة في جدول الرسائل: {columns}")

        # إضافة الأعمدة الجديدة إذا لم تكن موجودة
        if 'is_multi_recipient' not in columns:
            debug_print("إضافة عمود is_multi_recipient...")
            cursor.execute("ALTER TABLE message ADD COLUMN is_multi_recipient BOOLEAN DEFAULT 0")

        if 'recipient_type' not in columns:
            debug_print("إضافة عمود recipient_type...")
            cursor.execute("ALTER TABLE message ADD COLUMN recipient_type VARCHAR(20) DEFAULT 'user'")

        # حفظ التغييرات
        conn.commit()

        # إغلاق الاتصال
        cursor.close()
        conn.close()

        # إنشاء الجداول الجديدة
        debug_print("جاري إنشاء الجداول الجديدة...")
        db.create_all()
        print("تم إنشاء الجداول الجديدة بنجاح")

        # التحقق من إنشاء الجداول
        inspector = db.inspect(db.engine)
        updated_tables = inspector.get_table_names()
        debug_print(f"الجداول بعد التحديث: {updated_tables}")

        # تحديث الرسائل الحالية
        debug_print("جاري تحديث الرسائل الحالية...")
        update_existing_messages()

        print("تم تحديث هيكل قاعدة البيانات بنجاح!")
        return True
    except Exception as e:
        print(f"حدث خطأ أثناء تحديث هيكل قاعدة البيانات: {str(e)}")
        traceback.print_exc()  # طباعة تفاصيل الخطأ
        return False

def update_existing_messages():
    """تحديث الرسائل الحالية لتتوافق مع النظام الجديد"""
    print("جاري تحديث الرسائل الحالية...")

    try:
        # الحصول على مسار قاعدة البيانات
        db_path = find_database_file()
        if not db_path:
            print("لم يتم العثور على قاعدة البيانات")
            return

        # الاتصال بقاعدة البيانات
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # الحصول على جميع الرسائل التي لها مستلم
        debug_print("جاري الحصول على الرسائل...")
        cursor.execute("SELECT id, recipient_id, status, is_archived FROM message WHERE recipient_id IS NOT NULL")
        messages = cursor.fetchall()
        debug_print(f"تم العثور على {len(messages)} رسالة")

        # التحقق من وجود جدول message_recipient
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message_recipient'")
        if not cursor.fetchone():
            print("جدول message_recipient غير موجود")
            return

        # إنشاء سجلات المستلمين
        count = 0
        for message in messages:
            message_id, recipient_id, status, is_archived = message

            # التحقق من عدم وجود سجل مستلم للرسالة
            cursor.execute("SELECT id FROM message_recipient WHERE message_id = ? AND recipient_id = ?", (message_id, recipient_id))
            if cursor.fetchone():
                debug_print(f"الرسالة {message_id} لها سجل مستلم بالفعل")
                continue

            # إنشاء سجل مستلم للرسالة
            debug_print(f"إنشاء سجل مستلم للرسالة {message_id}")
            cursor.execute(
                "INSERT INTO message_recipient (message_id, recipient_id, recipient_type, status, is_archived) VALUES (?, ?, ?, ?, ?)",
                (message_id, recipient_id, 'user', status or 'new', 1 if is_archived else 0)
            )
            count += 1

        # حفظ التغييرات
        conn.commit()

        # إغلاق الاتصال
        cursor.close()
        conn.close()

        print(f"تم تحديث {count} رسالة")
    except Exception as e:
        print(f"حدث خطأ أثناء تحديث الرسائل: {str(e)}")
        traceback.print_exc()  # طباعة تفاصيل الخطأ

def create_default_groups():
    """إنشاء مجموعات افتراضية"""
    print("جاري إنشاء المجموعات الافتراضية...")

    try:
        # التحقق من وجود مستخدم مدير النظام
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            print("لم يتم العثور على مستخدم مدير النظام")
            return

        # التحقق من وجود مجموعة جميع المستخدمين
        all_users_group = UserGroup.query.filter_by(name="جميع المستخدمين").first()
        if not all_users_group:
            # إنشاء مجموعة لجميع المستخدمين
            all_users_group = UserGroup(
                name="جميع المستخدمين",
                description="مجموعة تضم جميع مستخدمي النظام",
                created_by_id=admin.id,
                is_public=True,
                is_active=True
            )

            db.session.add(all_users_group)
            db.session.commit()

            # إضافة المنشئ كمشرف في المجموعة
            admin_membership = UserGroupMembership(
                group_id=all_users_group.id,
                user_id=admin.id,
                role='admin'
            )
            db.session.add(admin_membership)
            db.session.commit()

            # إضافة جميع المستخدمين الآخرين كأعضاء
            users = User.query.filter(User.id != admin.id).all()
            for user in users:
                # التحقق من عدم وجود عضوية
                existing_membership = UserGroupMembership.query.filter_by(
                    group_id=all_users_group.id,
                    user_id=user.id
                ).first()

                if not existing_membership:
                    membership = UserGroupMembership(
                        group_id=all_users_group.id,
                        user_id=user.id,
                        role='member'
                    )
                    db.session.add(membership)

            db.session.commit()

        # إنشاء مجموعات حسب الأقسام
        departments = {}
        for user in User.query.all():
            if user.department_name and user.department_name not in departments:
                departments[user.department_name] = []
            if user.department_name:
                departments[user.department_name].append(user.id)

        for dept_name, user_ids in departments.items():
            if not dept_name or not user_ids:
                continue

            # التحقق من وجود مجموعة القسم
            dept_group_name = f"قسم {dept_name}"
            dept_group = UserGroup.query.filter_by(name=dept_group_name).first()

            if not dept_group:
                dept_group = UserGroup(
                    name=dept_group_name,
                    description=f"مجموعة تضم مستخدمي قسم {dept_name}",
                    created_by_id=admin.id,
                    is_public=True,
                    is_active=True
                )

                db.session.add(dept_group)
                db.session.commit()

                # إضافة المنشئ كمشرف في المجموعة
                admin_membership = UserGroupMembership(
                    group_id=dept_group.id,
                    user_id=admin.id,
                    role='admin'
                )
                db.session.add(admin_membership)
                db.session.commit()

                # إضافة أعضاء القسم
                for user_id in user_ids:
                    # التحقق من عدم وجود عضوية
                    existing_membership = UserGroupMembership.query.filter_by(
                        group_id=dept_group.id,
                        user_id=user_id
                    ).first()

                    if not existing_membership:
                        membership = UserGroupMembership(
                            group_id=dept_group.id,
                            user_id=user_id,
                            role='member'
                        )
                        db.session.add(membership)

                db.session.commit()

        print("تم إنشاء المجموعات الافتراضية بنجاح")
    except Exception as e:
        print(f"حدث خطأ أثناء إنشاء المجموعات الافتراضية: {str(e)}")
        traceback.print_exc()  # طباعة تفاصيل الخطأ

if __name__ == "__main__":
    with app.app_context():
        # تحديث هيكل قاعدة البيانات
        if update_database_schema():
            # إنشاء المجموعات الافتراضية
            create_default_groups()
            print("تم تحديث قاعدة البيانات بنجاح!")
        else:
            print("فشل تحديث قاعدة البيانات")
