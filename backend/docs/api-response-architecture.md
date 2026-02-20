# API 响应与状态码规范

## 目标
- HTTP 状态码表达传输/协议语义（2xx/4xx/5xx）。
- `code` 仅表达应用语义，前后端稳定约定，不与 HTTP 状态码复用。
- 业务细分错误通过 `error_code`（字符串）表达，避免依赖中文文案。

## 响应结构
```json
{
  "code": 0,
  "msg": "ok",
  "data": {}
}
```

错误示例：
```json
{
  "code": 100000,
  "msg": "存储空间不足",
  "data": {
    "error_code": "DISK_QUOTA_EXCEEDED"
  }
}
```

## 统一约定
- 成功：HTTP `200`，`code=0`。
- 参数校验失败：HTTP `422`，`code=100422`。
- 未认证：HTTP `401`，`code=100401` 或更细分如 `100101`（登录失败）。
- 无权限：HTTP `403`，`code=100403`。
- 业务失败：HTTP `400`，`code=100000`，可携带 `error_code`。
- 系统异常：HTTP `500`，`code=100500`。

## 演进策略
- 新功能必须返回 `code=0` 成功语义，失败走统一异常处理。
- 前端优先识别 `error_code`，其次识别 `code`，最后兜底 `msg`。
- 逐步将控制器中的 `ResponseModel.error(...)` 迁移为抛出业务异常，保证链路一致。

