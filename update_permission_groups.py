from app import app, db, PermissionGroup, Permission
import os

def update_permission_groups():
    """تحديث وإضافة مجموعات الصلاحيات وربطها بالصلاحيات"""
    
    with app.app_context():
        # قائمة مجموعات الصلاحيات المطلوبة
        required_groups = [
            # مجموعة إدارة المستخدمين
            {
                'name': 'user_management',
                'display_name': 'إدارة المستخدمين',
                'description': 'صلاحيات إدارة المستخدمين وحساباتهم',
                'icon': 'fa-users',
                'order': 1,
                'permissions': [
                    'manage_users', 'view_users', 'create_users', 
                    'edit_users', 'deactivate_users'
                ]
            },
            # مجموعة إدارة الأقسام
            {
                'name': 'department_management',
                'display_name': 'إدارة الأقسام',
                'description': 'صلاحيات إدارة الأقسام والوحدات التنظيمية',
                'icon': 'fa-building',
                'order': 2,
                'permissions': [
                    'manage_departments', 'view_departments', 'create_departments',
                    'edit_departments', 'delete_departments'
                ]
            },
            # مجموعة إدارة الأدوار والصلاحيات
            {
                'name': 'role_management',
                'display_name': 'إدارة الأدوار',
                'description': 'صلاحيات إدارة الأدوار والصلاحيات',
                'icon': 'fa-user-tag',
                'order': 3,
                'permissions': [
                    'manage_roles', 'view_roles', 'create_roles',
                    'edit_roles', 'delete_roles'
                ]
            },
            # مجموعة إدارة الصلاحيات
            {
                'name': 'permission_management',
                'display_name': 'إدارة الصلاحيات',
                'description': 'صلاحيات إدارة صلاحيات المستخدمين',
                'icon': 'fa-key',
                'order': 4,
                'permissions': [
                    'manage_permissions', 'view_permissions', 'assign_permissions'
                ]
            },
            # مجموعة إدارة الرسائل
            {
                'name': 'message_management',
                'display_name': 'إدارة الرسائل',
                'description': 'صلاحيات إدارة الرسائل والمراسلات',
                'icon': 'fa-envelope',
                'order': 5,
                'permissions': [
                    'manage_messages', 'view_all_messages', 'delete_messages',
                    'archive_messages'
                ]
            },
            # مجموعة إدارة حالة الرسائل
            {
                'name': 'message_status_management',
                'display_name': 'إدارة حالة الرسائل',
                'description': 'صلاحيات إدارة حالة الرسائل وتتبعها',
                'icon': 'fa-exchange-alt',
                'order': 6,
                'permissions': [
                    'change_message_status', 'view_message_status_history'
                ]
            },
            # مجموعة التقارير
            {
                'name': 'reports',
                'display_name': 'التقارير',
                'description': 'صلاحيات عرض وتصدير التقارير',
                'icon': 'fa-chart-bar',
                'order': 7,
                'permissions': [
                    'view_reports', 'export_reports'
                ]
            },
            # مجموعة إدارة النظام
            {
                'name': 'system_management',
                'display_name': 'إدارة النظام',
                'description': 'صلاحيات إدارة النظام وإعداداته',
                'icon': 'fa-cogs',
                'order': 8,
                'permissions': [
                    'view_system_logs', 'manage_system_settings'
                ]
            }
        ]
        
        # إضافة أو تحديث مجموعات الصلاحيات
        for group_data in required_groups:
            # البحث عن المجموعة
            group = PermissionGroup.query.filter_by(name=group_data['name']).first()
            
            if group:
                # تحديث المجموعة الموجودة
                group.display_name = group_data['display_name']
                group.description = group_data['description']
                group.icon = group_data['icon']
                group.order = group_data['order']
                print(f"تم تحديث مجموعة الصلاحيات: {group_data['name']} - {group_data['display_name']}")
            else:
                # إنشاء مجموعة جديدة
                group = PermissionGroup(
                    name=group_data['name'],
                    display_name=group_data['display_name'],
                    description=group_data['description'],
                    icon=group_data['icon'],
                    order=group_data['order']
                )
                db.session.add(group)
                db.session.flush()  # لضمان الحصول على معرف المجموعة
                print(f"تم إضافة مجموعة صلاحيات جديدة: {group_data['name']} - {group_data['display_name']}")
            
            # ربط الصلاحيات بالمجموعة
            for permission_name in group_data['permissions']:
                permission = Permission.query.filter_by(name=permission_name).first()
                if permission:
                    permission.group_id = group.id
                    print(f"  تم ربط الصلاحية '{permission_name}' بالمجموعة '{group_data['name']}'")
        
        # تحديد الصلاحيات الحساسة
        critical_permissions = [
            'manage_users', 'create_users', 'deactivate_users',
            'manage_roles', 'create_roles', 'edit_roles', 'delete_roles',
            'manage_permissions', 'assign_permissions',
            'delete_messages', 'manage_system_settings'
        ]
        
        for permission_name in critical_permissions:
            permission = Permission.query.filter_by(name=permission_name).first()
            if permission:
                permission.is_critical = True
                print(f"تم تحديد الصلاحية '{permission_name}' كصلاحية حساسة")
        
        # حفظ التغييرات
        db.session.commit()
        print("تم حفظ جميع التغييرات بنجاح!")

if __name__ == "__main__":
    # إنشاء مجلد instance إذا لم يكن موجودًا
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)
    
    # تحديث مجموعات الصلاحيات
    update_permission_groups()
