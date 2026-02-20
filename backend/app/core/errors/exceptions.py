"""
@File: exceptions.py
@Description: 统一业务异常定义
"""

from __future__ import annotations

from http import HTTPStatus

from app.core.errors.codes import (
    AuthCode,
    CommonCode,
    FileCode,
    OfficeCode,
    PermissionCode,
    ShareCode,
    UserCode,
)


class AppException(Exception):
    def __init__(self, http_status: int, code: int, message: str):
        self.http_status = int(http_status)
        self.code = int(code)
        self.message = message
        super().__init__(message)


class BadRequestException(AppException):
    def __init__(self, message: str = "请求参数错误"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=CommonCode.BAD_REQUEST,
            message=message,
        )


class ConflictException(AppException):
    def __init__(self, message: str = "资源冲突"):
        super().__init__(
            http_status=HTTPStatus.CONFLICT,
            code=CommonCode.CONFLICT,
            message=message,
        )


class InternalErrorException(AppException):
    def __init__(self, message: str = "系统内部错误"):
        super().__init__(
            http_status=HTTPStatus.INTERNAL_SERVER_ERROR,
            code=CommonCode.INTERNAL_ERROR,
            message=message,
        )


class ServiceUnavailableException(AppException):
    def __init__(self, message: str = "服务暂不可用"):
        super().__init__(
            http_status=HTTPStatus.SERVICE_UNAVAILABLE,
            code=CommonCode.INTERNAL_ERROR,
            message=message,
        )


class AuthException(AppException):
    pass


class PermissionException(AppException):
    pass


class FileException(AppException):
    pass


class ShareException(AppException):
    pass


class UserException(AppException):
    pass


class OfficeException(AppException):
    pass


class Unauthorized(AuthException):
    def __init__(self, message: str = "未登录或登录已失效"):
        super().__init__(
            http_status=HTTPStatus.UNAUTHORIZED,
            code=AuthCode.UNAUTHORIZED,
            message=message,
        )


class InvalidCredentials(AuthException):
    def __init__(self, message: str = "用户名或密码错误，请重新登录"):
        super().__init__(
            http_status=HTTPStatus.UNAUTHORIZED,
            code=AuthCode.INVALID_CREDENTIALS,
            message=message,
        )


class AccountDisabled(AuthException):
    def __init__(self, message: str = "账号已被禁用"):
        super().__init__(
            http_status=HTTPStatus.FORBIDDEN,
            code=AuthCode.ACCOUNT_DISABLED,
            message=message,
        )


class LoginRateLimited(AuthException):
    def __init__(self, message: str = "登录过于频繁，请稍后重试"):
        super().__init__(
            http_status=HTTPStatus.TOO_MANY_REQUESTS,
            code=AuthCode.LOGIN_RATE_LIMITED,
            message=message,
        )


class RefreshRateLimited(AuthException):
    def __init__(self, message: str = "刷新过于频繁，请稍后重试"):
        super().__init__(
            http_status=HTTPStatus.TOO_MANY_REQUESTS,
            code=AuthCode.REFRESH_RATE_LIMITED,
            message=message,
        )


class RefreshTokenInvalid(AuthException):
    def __init__(self, message: str = "刷新令牌无效，请重新登录"):
        super().__init__(
            http_status=HTTPStatus.UNAUTHORIZED,
            code=AuthCode.REFRESH_TOKEN_INVALID,
            message=message,
        )


class SessionEnvChanged(AuthException):
    def __init__(self, message: str = "检测到登录环境变更，请重新登录"):
        super().__init__(
            http_status=HTTPStatus.UNAUTHORIZED,
            code=AuthCode.SESSION_ENV_CHANGED,
            message=message,
        )


class TokenExpired(AuthException):
    def __init__(self, message: str = "登录已过期，请重新登录"):
        super().__init__(
            http_status=HTTPStatus.UNAUTHORIZED,
            code=AuthCode.TOKEN_EXPIRED,
            message=message,
        )


class UserNotFound(UserException):
    def __init__(self, message: str = "用户不存在"):
        super().__init__(
            http_status=HTTPStatus.NOT_FOUND,
            code=UserCode.USER_NOT_FOUND,
            message=message,
        )


class UserConflict(UserException):
    def __init__(self, message: str = "用户资源冲突"):
        super().__init__(
            http_status=HTTPStatus.CONFLICT,
            code=UserCode.USER_CONFLICT,
            message=message,
        )


class NoPermission(PermissionException):
    def __init__(self, message: str = "无权限访问该资源"):
        super().__init__(
            http_status=HTTPStatus.FORBIDDEN,
            code=PermissionCode.NO_PERMISSION,
            message=message,
        )


class FileNotFound(FileException):
    def __init__(self, message: str = "文件不存在"):
        super().__init__(
            http_status=HTTPStatus.NOT_FOUND,
            code=FileCode.FILE_NOT_FOUND,
            message=message,
        )


class ParentNotDirectory(FileException):
    def __init__(self, message: str = "父节点不是目录"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=FileCode.PARENT_NOT_DIR,
            message=message,
        )


class NameConflict(FileException):
    def __init__(self, message: str = "同级目录下已存在同名资源"):
        super().__init__(
            http_status=HTTPStatus.CONFLICT,
            code=FileCode.NAME_CONFLICT,
            message=message,
        )


class StorageMismatch(FileException):
    def __init__(self, message: str = "目标目录存储不一致"):
        super().__init__(
            http_status=HTTPStatus.CONFLICT,
            code=FileCode.STORAGE_MISMATCH,
            message=message,
        )


class RestoreParentMissing(FileException):
    def __init__(self, message: str = "上级目录不存在，无法恢复"):
        super().__init__(
            http_status=HTTPStatus.CONFLICT,
            code=FileCode.RESTORE_PARENT_MISSING,
            message=message,
        )


class RestoreParentDeleted(FileException):
    def __init__(self, message: str = "请先恢复上级目录"):
        super().__init__(
            http_status=HTTPStatus.CONFLICT,
            code=FileCode.RESTORE_PARENT_DELETED,
            message=message,
        )


class MoveToSelf(FileException):
    def __init__(self, message: str = "不允许移动到自身"):
        super().__init__(
            http_status=HTTPStatus.CONFLICT,
            code=FileCode.MOVE_TO_SELF,
            message=message,
        )


class MoveToDescendant(FileException):
    def __init__(self, message: str = "不允许移动到子目录"):
        super().__init__(
            http_status=HTTPStatus.CONFLICT,
            code=FileCode.MOVE_TO_DESCENDANT,
            message=message,
        )


class QuotaExceeded(FileException):
    def __init__(self, message: str = "存储空间不足"):
        super().__init__(
            http_status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            code=FileCode.QUOTA_EXCEEDED,
            message=message,
        )


class PayloadTooLarge(FileException):
    def __init__(self, message: str = "上传文件超过限制"):
        super().__init__(
            http_status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            code=FileCode.PAYLOAD_TOO_LARGE,
            message=message,
        )


class StorageConfigNotFound(FileException):
    def __init__(self, message: str = "存储配置不存在"):
        super().__init__(
            http_status=HTTPStatus.NOT_FOUND,
            code=FileCode.STORAGE_CONFIG_NOT_FOUND,
            message=message,
        )


class InvalidPage(FileException):
    def __init__(self, message: str = "页码不合法"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=FileCode.INVALID_PAGE,
            message=message,
        )


class InvalidPageSize(FileException):
    def __init__(self, message: str = "分页大小不合法"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=FileCode.INVALID_PAGE_SIZE,
            message=message,
        )


class InvalidTargetType(FileException):
    def __init__(self, message: str = "目标不是文件"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=FileCode.INVALID_TARGET_TYPE,
            message=message,
        )


class InvalidFileName(FileException):
    def __init__(self, message: str = "文件名不合法"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=FileCode.INVALID_FILE_NAME,
            message=message,
        )


class InvalidPartNumber(FileException):
    def __init__(self, message: str = "分片编号不合法"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=FileCode.INVALID_PART_NUMBER,
            message=message,
        )


class InvalidUploadId(FileException):
    def __init__(self, message: str = "上传会话ID不合法"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=FileCode.INVALID_UPLOAD_ID,
            message=message,
        )


class InvalidTotalParts(FileException):
    def __init__(self, message: str = "分片总数不合法"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=FileCode.INVALID_TOTAL_PARTS,
            message=message,
        )


class FileTokenInvalid(FileException):
    def __init__(self, message: str = "令牌无效"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=FileCode.TOKEN_INVALID,
            message=message,
        )


class FileTokenExpired(FileException):
    def __init__(self, message: str = "令牌已过期"):
        super().__init__(
            http_status=HTTPStatus.GONE,
            code=FileCode.TOKEN_EXPIRED,
            message=message,
        )


class PreviewNotSupported(FileException):
    def __init__(self, message: str = "目录不支持预览"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=FileCode.PREVIEW_NOT_SUPPORTED,
            message=message,
        )


class ThumbnailNotSupported(FileException):
    def __init__(self, message: str = "当前文件类型不支持缩略图"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=FileCode.THUMBNAIL_NOT_SUPPORTED,
            message=message,
        )


class ThumbnailBuildFailed(FileException):
    def __init__(self, message: str = "缩略图生成失败"):
        super().__init__(
            http_status=HTTPStatus.INTERNAL_SERVER_ERROR,
            code=FileCode.THUMBNAIL_BUILD_FAILED,
            message=message,
        )


class ZipTargetRequired(FileException):
    def __init__(self, message: str = "缺少压缩目标"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=FileCode.ZIP_TARGET_REQUIRED,
            message=message,
        )


class ZipTooManyConflicts(FileException):
    def __init__(self, message: str = "压缩失败：重名过多"):
        super().__init__(
            http_status=HTTPStatus.CONFLICT,
            code=FileCode.ZIP_TOO_MANY_CONFLICTS,
            message=message,
        )


class TaskNotReady(FileException):
    def __init__(self, message: str = "任务尚未完成"):
        super().__init__(
            http_status=HTTPStatus.CONFLICT,
            code=FileCode.TASK_NOT_READY,
            message=message,
        )


class TaskInvalid(FileException):
    def __init__(self, message: str = "任务无效"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=FileCode.TASK_INVALID,
            message=message,
        )


class UploadSessionNotFound(FileException):
    def __init__(self, message: str = "上传会话不存在"):
        super().__init__(
            http_status=HTTPStatus.NOT_FOUND,
            code=FileCode.UPLOAD_SESSION_NOT_FOUND,
            message=message,
        )


class ChunkIncomplete(FileException):
    def __init__(self, message: str = "分片不完整"):
        super().__init__(
            http_status=HTTPStatus.CONFLICT,
            code=FileCode.CHUNK_INCOMPLETE,
            message=message,
        )


class UploadFinalizing(FileException):
    def __init__(self, message: str = "上传正在合并"):
        super().__init__(
            http_status=HTTPStatus.CONFLICT,
            code=FileCode.UPLOAD_FINALIZING,
            message=message,
        )


class UploadSessionCompleted(FileException):
    def __init__(self, message: str = "上传会话已完成"):
        super().__init__(
            http_status=HTTPStatus.CONFLICT,
            code=FileCode.FILE_STATE_CONFLICT,
            message=message,
        )


class ShareNotFound(ShareException):
    def __init__(self, message: str = "分享不存在"):
        super().__init__(
            http_status=HTTPStatus.NOT_FOUND,
            code=ShareCode.SHARE_NOT_FOUND,
            message=message,
        )


class ShareExpired(ShareException):
    def __init__(self, message: str = "分享已过期"):
        super().__init__(
            http_status=HTTPStatus.GONE,
            code=ShareCode.SHARE_EXPIRED,
            message=message,
        )


class ShareRevoked(ShareException):
    def __init__(self, message: str = "分享已取消"):
        super().__init__(
            http_status=HTTPStatus.GONE,
            code=ShareCode.SHARE_REVOKED,
            message=message,
        )


class ShareResourceNotFound(ShareException):
    def __init__(self, message: str = "分享文件已被删除"):
        super().__init__(
            http_status=HTTPStatus.NOT_FOUND,
            code=ShareCode.SHARE_RESOURCE_NOT_FOUND,
            message=message,
        )


class ShareCodeInvalid(ShareException):
    def __init__(self, message: str = "提取码错误"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=ShareCode.SHARE_CODE_INVALID,
            message=message,
        )


class ShareCodeRequired(ShareException):
    def __init__(self, message: str = "需要提取码"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=ShareCode.SHARE_CODE_REQUIRED,
            message=message,
        )


class ShareInvalidExpireAt(ShareException):
    def __init__(self, message: str = "有效期必须晚于当前时间"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=ShareCode.SHARE_INVALID_EXPIRE_AT,
            message=message,
        )


class ShareNotFolder(ShareException):
    def __init__(self, message: str = "分享不是目录"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=ShareCode.SHARE_NOT_FOLDER,
            message=message,
        )


class ShareOutOfScope(ShareException):
    def __init__(self, message: str = "资源不在分享范围内"):
        super().__init__(
            http_status=HTTPStatus.FORBIDDEN,
            code=ShareCode.SHARE_OUT_OF_SCOPE,
            message=message,
        )


class OfficeUnavailable(OfficeException):
    def __init__(self, message: str = "Office 在线预览未启用"):
        super().__init__(
            http_status=HTTPStatus.SERVICE_UNAVAILABLE,
            code=OfficeCode.OFFICE_UNAVAILABLE,
            message=message,
        )


class OfficeTokenInvalid(OfficeException):
    def __init__(self, message: str = "WOPI 访问令牌无效"):
        super().__init__(
            http_status=HTTPStatus.BAD_REQUEST,
            code=OfficeCode.OFFICE_TOKEN_INVALID,
            message=message,
        )


class OfficeTokenExpired(OfficeException):
    def __init__(self, message: str = "WOPI 访问令牌已过期"):
        super().__init__(
            http_status=HTTPStatus.GONE,
            code=OfficeCode.OFFICE_TOKEN_EXPIRED,
            message=message,
        )


class OfficeForbidden(OfficeException):
    def __init__(self, message: str = "WOPI 请求来源不被允许"):
        super().__init__(
            http_status=HTTPStatus.FORBIDDEN,
            code=OfficeCode.OFFICE_FORBIDDEN,
            message=message,
        )
