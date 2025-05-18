from app import app, db, Permission, Role
import os

def update_permissions():
    """تحديث وإضافة صلاحيات جديدة للنظام"""
    
    with app.app_context():
        # قائمة الصلاحيات المطلوبة مع أسمائها العربية ووصفها
        required_permissions = [
            # صلاحيات إدارة المستخدمين
            ('manage_users', 'إدارة المستخدمين', 'إنشاء وتعديل وتعطيل حسابات المستخدمين'),
            ('view_users', 'عرض المستخدمين', 'عرض قائمة المستخدمين'),
            ('create_users', 'إنشاء مستخدمين', 'إنشاء حسابات مستخدمين جديدة'),
            ('edit_users', 'تعديل المستخدمين', 'تعديل بيانات المستخدمين'),
            ('deactivate_users', 'تعطيل المستخدمين', 'تعطيل وتفعيل حسابات المستخدمين'),
            
            # صلاحيات إدارة الأقسام
            ('manage_departments', 'إدارة الأقسام', 'إنشاء وتعديل وحذف الأقسام'),
            ('view_departments', 'عرض الأقسام', 'عرض قائمة الأقسام'),
            ('create_departments', 'إنشاء أقسام', 'إنشاء أقسام جديدة'),
            ('edit_departments', 'تعديل الأقسام', 'تعديل بيانات الأقسام'),
            ('delete_departments', 'حذف الأقسام', 'حذف الأقسام'),
            
            # صلاحيات إدارة الأدوار والصلاحيات
            ('manage_roles', 'إدارة الأدوار', 'إنشاء وتعديل وحذف الأدوار'),
            ('view_roles', 'عرض الأدوار', 'عرض قائمة الأدوار'),
            ('create_roles', 'إنشاء أدوار', 'إنشاء أدوار جديدة'),
            ('edit_roles', 'تعديل الأدوار', 'تعديل بيانات الأدوار'),
            ('delete_roles', 'حذف الأدوار', 'حذف الأدوار'),
            
            # صلاحيات إدارة الصلاحيات
            ('manage_permissions', 'إدارة الصلاحيات', 'إدارة صلاحيات المستخدمين'),
            ('view_permissions', 'عرض الصلاحيات', 'عرض قائمة الصلاحيات'),
            ('assign_permissions', 'تعيين الصلاحيات', 'تعيين الصلاحيات للمستخدمين'),
            
            # صلاحيات إدارة الرسائل
            ('manage_messages', 'إدارة الرسائل', 'إدارة جميع الرسائل في النظام'),
            ('view_all_messages', 'عرض جميع الرسائل', 'عرض جميع الرسائل في النظام'),
            ('delete_messages', 'حذف الرسائل', 'حذف الرسائل'),
            ('archive_messages', 'أرشفة الرسائل', 'أرشفة الرسائل'),
            
            # صلاحيات إدارة حالة الرسائل
            ('change_message_status', 'تغيير حالة الرسائل', 'تغيير حالة الرسائل'),
            ('view_message_status_history', 'عرض سجل حالة الرسائل', 'عرض سجل تغييرات حالة الرسائل'),
            
            # صلاحيات التقارير
            ('view_reports', 'عرض التقارير', 'عرض تقارير النظام'),
            ('export_reports', 'تصدير التقارير', 'تصدير تقارير النظام'),
            
            # صلاحيات النظام
            ('view_system_logs', 'عرض سجلات النظام', 'عرض سجلات النظام'),
            ('manage_system_settings', 'إدارة إعدادات النظام', 'تعديل إعدادات النظام')
        ]
        
        # إضافة أو تحديث الصلاحيات
        for name, display_name, description in required_permissions:
            # البحث عن الصلاحية
            permission = Permission.query.filter_by(name=name).first()
            
            if permission:
                # تحديث الصلاحية الموجودة
                permission.display_name = display_name
                permission.description = description
                print(f"تم تحديث الصلاحية: {name} - {display_name}")
            else:
                # إنشاء صلاحية جديدة
                new_permission = Permission(
                    name=name,
                    display_name=display_name,
                    description=description
                )
                db.session.add(new_permission)
                print(f"تم إضافة صلاحية جديدة: {name} - {display_name}")
        
        # تحديث صلاحيات دور المشرف (admin)
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role:
            # الحصول على جميع الصلاحيات
            all_permissions = Permission.query.all()
            
            # إضافة جميع الصلاحيات لدور المشرف
            admin_role.permissions = all_permissions
            print(f"تم تحديث صلاحيات دور المشرف بإجمالي {len(all_permissions)} صلاحية")
        
        # حفظ التغييرات
        db.session.commit()
        print("تم حفظ جميع التغييرات بنجاح!")

if __name__ == "__main__":
    # إنشاء مجلد instance إذا لم يكن موجودًا
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)
    
    # تحديث الصلاحيات
    update_permissions()
