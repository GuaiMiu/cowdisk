-- 安装初始化：后台菜单与角色授权（兼容 SQLite/MySQL）
-- 注意：BN_SYSMENU/BN_SYSROLE 存在多列非空约束，必须写全关键字段。

-- 系统管理目录
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 100, '系统管理', 'admin-system', 0, 'settings', 1, NULL, 100, NULL, '', 1, NULL, 1, 0, '系统管理目录', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 100);

-- 权限配置目录
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 110, '权限配置', 'admin-access', 100, 'shield', 1, NULL, 10, NULL, 'access', 1, NULL, 1, 0, '用户/角色/菜单管理', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 110);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 111, '用户管理', 'admin-access-user', 110, 'users', 2, 'system:user:view', 10, NULL, 'user', 1, '/views/admin/system/UserView.vue', 1, 0, '用户管理页面', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 111);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 112, '角色管理', 'admin-access-role', 110, 'shield-check', 2, 'system:role:view', 20, NULL, 'role', 1, '/views/admin/system/RoleView.vue', 1, 0, '角色管理页面', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 112);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 113, '菜单管理', 'admin-access-menu', 110, 'menu-square', 2, 'system:menu:view', 30, NULL, 'menu', 1, '/views/admin/system/MenuView.vue', 1, 0, '菜单管理页面', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 113);

-- 系统配置目录
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 120, '系统配置', 'admin-config', 100, 'settings', 1, NULL, 20, NULL, 'config', 1, NULL, 1, 0, '配置中心目录', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 120);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 121, '基础配置', 'admin-config-system', 120, 'settings', 2, 'cfg:core:read', 10, NULL, 'system', 1, '/views/admin/system/SystemConfigView.vue', 1, 0, '系统配置页（含性能与传输）', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 121);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 122, '审计中心', 'admin-config-audit', 120, 'shield-check', 2, 'cfg:audit:read', 20, NULL, 'audit', 1, '/views/admin/system/AuditView.vue', 1, 0, '审计配置与审计日志', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 122);

-- 网盘权限目录（隐藏，仅用于权限编排）
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 200, '网盘权限', 'disk-permissions', 0, 'hard-drive', 1, NULL, 200, NULL, 'disk-permissions', 1, NULL, 1, 0, '网盘权限编排目录', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 200);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 201, '文件管理', NULL, 200, NULL, 2, 'disk:file:view', 10, NULL, NULL, 1, NULL, 1, 0, '网盘文件权限分组', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 201);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 202, '分享管理', NULL, 200, NULL, 2, 'disk:share:view', 20, NULL, NULL, 1, NULL, 1, 0, '网盘分享权限分组', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 202);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 203, '回收站', NULL, 200, NULL, 2, 'disk:trash:view', 30, NULL, NULL, 1, NULL, 1, 0, '网盘回收站权限分组', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 203);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 204, '上传管理', NULL, 200, NULL, 2, NULL, 40, NULL, NULL, 1, NULL, 1, 0, '网盘上传权限分组', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 204);

-- 按钮权限（type=3）
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 1110, '用户列表', NULL, 111, NULL, 3, 'system:user:list', 5, NULL, NULL, 1, NULL, 1, 0, '用户列表权限', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 1110);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 1111, '用户新增', NULL, 111, NULL, 3, 'system:user:create', 10, NULL, NULL, 1, NULL, 1, 0, '用户新增按钮', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 1111);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 1112, '用户编辑', NULL, 111, NULL, 3, 'system:user:update', 20, NULL, NULL, 1, NULL, 1, 0, '用户编辑按钮', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 1112);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 1113, '用户删除', NULL, 111, NULL, 3, 'system:user:delete', 30, NULL, NULL, 1, NULL, 1, 0, '用户删除按钮', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 1113);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 1120, '角色列表', NULL, 112, NULL, 3, 'system:role:list', 5, NULL, NULL, 1, NULL, 1, 0, '角色列表权限', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 1120);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 1121, '角色新增', NULL, 112, NULL, 3, 'system:role:create', 10, NULL, NULL, 1, NULL, 1, 0, '角色新增按钮', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 1121);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 1122, '角色编辑', NULL, 112, NULL, 3, 'system:role:update', 20, NULL, NULL, 1, NULL, 1, 0, '角色编辑按钮', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 1122);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 1123, '角色删除', NULL, 112, NULL, 3, 'system:role:delete', 30, NULL, NULL, 1, NULL, 1, 0, '角色删除按钮', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 1123);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 1130, '菜单列表', NULL, 113, NULL, 3, 'system:menu:list', 5, NULL, NULL, 1, NULL, 1, 0, '菜单列表权限', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 1130);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 1131, '菜单新增', NULL, 113, NULL, 3, 'system:menu:create', 10, NULL, NULL, 1, NULL, 1, 0, '菜单新增按钮', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 1131);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 1132, '菜单编辑', NULL, 113, NULL, 3, 'system:menu:update', 20, NULL, NULL, 1, NULL, 1, 0, '菜单编辑按钮', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 1132);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 1133, '菜单删除', NULL, 113, NULL, 3, 'system:menu:delete', 30, NULL, NULL, 1, NULL, 1, 0, '菜单删除按钮', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 1133);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 1211, '配置写入', NULL, 121, NULL, 3, 'cfg:core:write', 10, NULL, NULL, 1, NULL, 1, 0, '系统配置写入', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 1211);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 1212, '上传清理', NULL, 121, NULL, 3, 'cfg:upload:operate', 20, NULL, NULL, 1, NULL, 1, 0, '上传分片清理操作', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 1212);

INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 1221, '审计操作', NULL, 122, NULL, 3, 'cfg:audit:operate', 10, NULL, NULL, 1, NULL, 1, 0, '审计导出与清理', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 1221);

SELECT 2101, '文件列表', NULL, 201, NULL, 3, 'disk:file:list', 10, NULL, NULL, 1, NULL, 1, 0, '查看文件列表', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2101);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2102, '新建目录', NULL, 201, NULL, 3, 'disk:file:mkdir', 20, NULL, NULL, 1, NULL, 1, 0, '新建目录', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2102);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2103, '上传文件', NULL, 201, NULL, 3, 'disk:file:upload', 30, NULL, NULL, 1, NULL, 1, 0, '上传文件', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2103);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2104, '编辑文件', NULL, 201, NULL, 3, 'disk:file:edit', 40, NULL, NULL, 1, NULL, 1, 0, '重命名/编辑', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2104);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2105, '移动文件', NULL, 201, NULL, 3, 'disk:file:move', 50, NULL, NULL, 1, NULL, 1, 0, '移动文件', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2105);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2106, '删除文件', NULL, 201, NULL, 3, 'disk:file:delete', 60, NULL, NULL, 1, NULL, 1, 0, '删除文件', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2106);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2107, '下载文件', NULL, 201, NULL, 3, 'disk:file:download', 70, NULL, NULL, 1, NULL, 1, 0, '下载文件', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2107);
SELECT 2108, '分享列表', NULL, 202, NULL, 3, 'disk:share:list', 80, NULL, NULL, 1, NULL, 1, 0, '查看分享', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2108);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2109, '创建分享', NULL, 202, NULL, 3, 'disk:share:create', 90, NULL, NULL, 1, NULL, 1, 0, '创建分享', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2109);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2110, '更新分享', NULL, 202, NULL, 3, 'disk:share:update', 100, NULL, NULL, 1, NULL, 1, 0, '更新分享', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2110);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2111, '删除分享', NULL, 202, NULL, 3, 'disk:share:delete', 110, NULL, NULL, 1, NULL, 1, 0, '删除分享', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2111);
SELECT 2112, '回收站查看', NULL, 203, NULL, 3, 'disk:trash:list', 120, NULL, NULL, 1, NULL, 1, 0, '查看回收站', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2112);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2113, '回收站恢复', NULL, 203, NULL, 3, 'disk:trash:restore', 130, NULL, NULL, 1, NULL, 1, 0, '恢复回收站文件', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2113);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2114, '回收站删除', NULL, 203, NULL, 3, 'disk:trash:delete', 140, NULL, NULL, 1, NULL, 1, 0, '删除回收站文件', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2114);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2115, '回收站清空', NULL, 203, NULL, 3, 'disk:trash:clear', 150, NULL, NULL, 1, NULL, 1, 0, '清空回收站', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2115);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2116, '分片上传初始化', NULL, 204, NULL, 3, 'disk:upload:init', 160, NULL, NULL, 1, NULL, 1, 0, '上传初始化', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2116);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2117, '分片上传完成', NULL, 204, NULL, 3, 'disk:upload:finalize', 170, NULL, NULL, 1, NULL, 1, 0, '上传完成提交', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2117);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2118, '分片上传分块', NULL, 204, NULL, 3, 'disk:upload:part', 180, NULL, NULL, 1, NULL, 1, 0, '上传分块', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2118);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2119, '分片上传状态', NULL, 204, NULL, 3, 'disk:upload:status', 190, NULL, NULL, 1, NULL, 1, 0, '查询上传状态', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2119);
INSERT INTO BN_SYSMENU
(id, name, route_name, pid, icon, type, permission_char, sort, redirect, router_path, keep_alive, component_path, status, is_frame, description, is_deleted, create_time, update_time)
SELECT 2120, '分片上传取消', NULL, 204, NULL, 3, 'disk:upload:cancel', 200, NULL, NULL, 1, NULL, 1, 0, '取消上传任务', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSMENU WHERE id = 2120);

-- 角色初始化
INSERT INTO BN_SYSROLE
(id, name, permission_char, status, description, is_deleted, update_time, update_by, create_by, create_time)
SELECT 1, '管理员', 'system:admin:*', 1, '后台管理员角色', 0, CURRENT_TIMESTAMP, NULL, NULL, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE WHERE id = 1);

INSERT INTO BN_SYSROLE
(id, name, permission_char, status, description, is_deleted, update_time, update_by, create_by, create_time)
SELECT 2, '普通用户', 'disk:user:*', 1, '默认普通用户角色（网盘权限）', 0, CURRENT_TIMESTAMP, NULL, NULL, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE WHERE id = 2);

-- 系统管理员角色默认菜单授权
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 100 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 100);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 110 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 110);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 111 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 111);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 1110 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 1110);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 112 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 112);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 1120 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 1120);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 113 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 113);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 1130 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 1130);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 120 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 120);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 121 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 121);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 122 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 122);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 1111 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 1111);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 1112 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 1112);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 1113 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 1113);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 1121 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 1121);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 1122 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 1122);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 1123 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 1123);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 1131 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 1131);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 1132 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 1132);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 1133 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 1133);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 1211 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 1211);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 1212 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 1212);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 1, 1221 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 1 AND menu_id = 1221);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2101 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2101);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2102 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2102);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2103 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2103);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2104 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2104);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2105 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2105);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2106 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2106);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2107 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2107);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2108 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2108);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2109 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2109);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2110 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2110);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2111 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2111);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2112 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2112);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2113 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2113);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2114 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2114);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2115 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2115);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2116 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2116);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2117 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2117);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2118 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2118);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2119 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2119);
INSERT INTO BN_SYSROLE_MENU (role_id, menu_id)
SELECT 2, 2120 WHERE NOT EXISTS (SELECT 1 FROM BN_SYSROLE_MENU WHERE role_id = 2 AND menu_id = 2120);

