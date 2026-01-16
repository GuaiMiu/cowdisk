"""
@File: password.py
@Author: GuaiMiu
@Date: 2025/3/19 16:35
@Version: 1.0
@Description:
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class PwdUtil:
    """
    密码工具类
    """

    @classmethod
    def verify_password(cls, plain_password, hashed_password):
        """
        :param plain_password: 输入密码
        :param hashed_password: 存储密码
        :return:
        """
        return pwd_context.verify(plain_password, hashed_password)

    @classmethod
    def get_password_hash(cls, input_password):
        """
        :param input_password: 输入的密码
        :return: 加密成功的密码
        """
        return pwd_context.hash(input_password)
