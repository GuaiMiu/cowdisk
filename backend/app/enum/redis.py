"""
@File: redis.py
@Author: GuaiMiu
@Date: 2025/4/4 00:48
@Version: 1.0
@Description:
"""

from enum import Enum


class RedisInitKeyEnum(Enum):
    """
    系统内置Redis键名
    """

    @property
    def key(self):
        return self.value.get("key")

    @property
    def remark(self):
        return self.value.get("remark")

    ACCESS_TOKEN = {"key": "access_token", "remark": "登录令牌信息"}
    REFRESH_TOKEN = {"key": "refresh_token", "remark": "刷新令牌信息"}
    DEVICE_INFO = {"key": "device_info", "remark": "用户设备信息"}
    DEVICE_STATUS = {"key": "device_status", "remark": "用户设备状态"}
    USER_SESSIONS = {"key": "user_sessions", "remark": "用户登录会话"}
    USER_INFO = {"key": "user_info", "remark": "用户信息"}
    USER_PERMISSIONS = {"key": "user_permissions", "remark": "用户权限"}
    USER_ROLES = {"key": "user_roles", "remark": "用户角色"}
    USER_MENU = {"key": "user_menu", "remark": "用户菜单"}
    SYS_DICT = {"key": "sys_dict", "remark": "数据字典"}
    SYS_CONFIG = {"key": "sys_config", "remark": "配置信息"}
    CAPTCHA_CODES = {"key": "captcha_codes", "remark": "图片验证码"}
    ACCOUNT_LOCK = {"key": "account_lock", "remark": "用户锁定"}
    PASSWORD_ERROR_COUNT = {"key": "password_error_count", "remark": "密码错误次数"}
    SESSION_META = {"key": "session_meta", "remark": "会话元数据(设备指纹等)"}
    AUTH_RATE_LIMIT = {"key": "auth_rate_limit", "remark": "认证接口限流计数"}
    REFRESH_ROTATE = {"key": "refresh_rotate", "remark": "刷新轮换计数"}
