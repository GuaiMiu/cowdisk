# 业务码表（AA BB CC）

编码规则：`AA BB CC`（6位整数）
- `AA` 模块：10系统、20认证、30用户、40文件、50权限、60分享、70协作
- `BB` 子模块：`00` 通用，其他按域细分
- `CC` 具体错误：`01-99`

## 系统（10xxxx）

| Code | 名称 | 含义 | 建议 HTTP |
|---|---|---|---|
| 100000 | OK | 成功（唯一成功码） | 2xx |
| 100001 | INTERNAL_ERROR | 系统内部错误 | 500 |
| 100002 | BAD_REQUEST | 请求参数错误/校验失败 | 400 |
| 100003 | CONFLICT | 通用冲突 | 409 |
| 100004 | RATE_LIMITED | 触发限流 | 429 |

## 认证（20xxxx）

| Code | 名称 | 含义 | 建议 HTTP |
|---|---|---|---|
| 200001 | UNAUTHORIZED | 未登录或会话失效 | 401 |
| 200002 | TOKEN_EXPIRED | Token 过期 | 401 |
| 200003 | TOKEN_INVALID | Token 非法 | 401 |
| 200011 | INVALID_CREDENTIALS | 用户名或密码错误 | 401 |
| 200012 | ACCOUNT_DISABLED | 账号已禁用 | 403 |
| 200013 | LOGIN_RATE_LIMITED | 登录频率超限 | 429 |
| 200021 | REFRESH_TOKEN_INVALID | 刷新令牌无效 | 401 |
| 200022 | SESSION_ENV_CHANGED | 登录环境变更 | 401 |
| 200023 | REFRESH_RATE_LIMITED | 刷新频率超限 | 429 |

## 用户（30xxxx）

| Code | 名称 | 含义 | 建议 HTTP |
|---|---|---|---|
| 300001 | USER_NOT_FOUND | 用户不存在 | 404 |
| 300002 | USER_CONFLICT | 用户资源冲突 | 409 |
| 300003 | USER_DISABLED | 用户被禁用 | 403 |

## 文件（40xxxx）

| Code | 名称 | 含义 | 建议 HTTP |
|---|---|---|---|
| 400001 | FILE_NOT_FOUND | 文件不存在 | 404 |
| 400002 | INVALID_FILE_REQUEST | 文件请求参数非法 | 400 |
| 400003 | INVALID_PAGE | 页码非法 | 400 |
| 400004 | INVALID_PAGE_SIZE | 分页大小非法 | 400 |
| 400005 | INVALID_TARGET_TYPE | 目标类型不匹配（如要求文件却给目录） | 400 |
| 400006 | PARENT_NOT_DIR | 父节点不是目录 | 400 |
| 400011 | NAME_CONFLICT | 同名冲突 | 409 |
| 400012 | FILE_STATE_CONFLICT | 文件状态冲突 | 409 |
| 400013 | RESTORE_PARENT_MISSING | 恢复失败：上级不存在 | 409 |
| 400014 | RESTORE_PARENT_DELETED | 恢复失败：上级仍在回收站 | 409 |
| 400015 | MOVE_TO_SELF | 不允许移动到自身 | 409 |
| 400016 | MOVE_TO_DESCENDANT | 不允许移动到子目录 | 409 |
| 400017 | STORAGE_MISMATCH | 存储不一致 | 409 |
| 400021 | QUOTA_EXCEEDED | 配额/空间不足 | 413 |
| 400022 | PAYLOAD_TOO_LARGE | 上传过大 | 413 |
| 400023 | STORAGE_CONFIG_NOT_FOUND | 存储配置不存在 | 404 |
| 400024 | TOKEN_INVALID | 文件下载/预览令牌非法 | 400 |
| 400025 | TOKEN_EXPIRED | 文件下载/预览令牌过期 | 410 |
| 400026 | PREVIEW_NOT_SUPPORTED | 不支持预览 | 400 |
| 400027 | THUMBNAIL_NOT_SUPPORTED | 不支持缩略图 | 400 |
| 400028 | THUMBNAIL_BUILD_FAILED | 缩略图生成失败 | 500 |
| 400029 | ZIP_TARGET_REQUIRED | 缺少压缩目标 | 400 |
| 400030 | ZIP_TOO_MANY_CONFLICTS | 压缩/解压命名冲突过多 | 409 |
| 400031 | UPLOAD_SESSION_NOT_FOUND | 上传会话不存在 | 404 |
| 400032 | CHUNK_INCOMPLETE | 分片不完整 | 409 |
| 400033 | UPLOAD_FINALIZING | 上传正在合并 | 409 |
| 400034 | INVALID_FILE_NAME | 文件名非法 | 400 |
| 400035 | INVALID_PART_NUMBER | 分片编号非法 | 400 |
| 400036 | INVALID_UPLOAD_ID | 上传会话 ID 非法 | 400 |
| 400037 | INVALID_TOTAL_PARTS | 分片总数非法 | 400 |
| 400038 | TASK_NOT_READY | 任务尚未完成 | 409 |
| 400039 | TASK_INVALID | 任务参数/状态无效 | 400 |

## 权限（50xxxx）

| Code | 名称 | 含义 | 建议 HTTP |
|---|---|---|---|
| 500001 | NO_PERMISSION | 无权限 | 403 |
| 500002 | SCOPE_DENIED | Scope 拒绝 | 403 |

## 分享（60xxxx）

| Code | 名称 | 含义 | 建议 HTTP |
|---|---|---|---|
| 600001 | SHARE_NOT_FOUND | 分享不存在 | 404 |
| 600002 | SHARE_TOKEN_INVALID | 分享令牌非法 | 404 |
| 600011 | SHARE_EXPIRED | 分享已过期/失效 | 410 |
| 600012 | SHARE_REVOKED | 分享已取消 | 410 |
| 600013 | SHARE_RESOURCE_NOT_FOUND | 分享目标已删除 | 404 |
| 600021 | SHARE_CODE_INVALID | 提取码错误 | 400 |
| 600022 | SHARE_CODE_REQUIRED | 需要提取码 | 400 |
| 600023 | SHARE_INVALID_EXPIRE_AT | 分享过期时间不合法 | 400 |
| 600024 | SHARE_NOT_FOLDER | 分享目标不是目录 | 400 |
| 600025 | SHARE_OUT_OF_SCOPE | 访问超出分享范围 | 403 |

## 协作/Office（70xxxx）

| Code | 名称 | 含义 | 建议 HTTP |
|---|---|---|---|
| 700001 | OFFICE_UNAVAILABLE | 协作服务不可用 | 503 |
| 700002 | OFFICE_TOKEN_INVALID | 协作令牌非法 | 401/403 |
| 700003 | OFFICE_TOKEN_EXPIRED | 协作令牌过期 | 410 |
| 700004 | OFFICE_FORBIDDEN | 协作访问被拒绝 | 403 |
