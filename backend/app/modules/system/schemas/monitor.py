"""
@File: monitor.py
@Author: GuaiMiu
@Date: 2026/02/19
@Version: 1.0
@Description: 系统监控 Schema
"""

from datetime import datetime

from pydantic import BaseModel, Field


class OnlineSessionOut(BaseModel):
    user_id: int = Field(..., description="用户 ID")
    username: str | None = Field(default=None, description="用户名")
    session_id: str = Field(..., description="会话 ID")
    login_ip: str | None = Field(default=None, description="登录 IP")
    user_agent: str | None = Field(default=None, description="客户端标识")
    token_ttl_seconds: int | None = Field(default=None, description="AccessToken 剩余秒数")


class OnlineUsersOut(BaseModel):
    total_users: int = Field(default=0, description="在线用户数")
    total_sessions: int = Field(default=0, description="在线会话数")
    sessions: list[OnlineSessionOut] = Field(default_factory=list, description="在线会话详情")


class ForceLogoutOut(BaseModel):
    session_id: str = Field(..., description="被强退的会话 ID")
    user_id: int | None = Field(default=None, description="会话所属用户 ID")
    success: bool = Field(default=True, description="是否强退成功")


class ServiceStatusOut(BaseModel):
    name: str = Field(..., description="服务标识")
    status: str = Field(..., description="服务状态: up/down/degraded")
    latency_ms: int | None = Field(default=None, description="探测耗时(毫秒)")
    detail: str | None = Field(default=None, description="服务说明")


class ServiceSummaryOut(BaseModel):
    total: int = Field(default=0, description="服务总数")
    up: int = Field(default=0, description="健康服务数")
    down: int = Field(default=0, description="异常服务数")
    degraded: int = Field(default=0, description="降级服务数")


class CpuStatusOut(BaseModel):
    usage_percent: float | None = Field(default=None, description="CPU 使用率(%)")
    logical_cores: int | None = Field(default=None, description="逻辑核心数")


class MemoryStatusOut(BaseModel):
    total_bytes: int | None = Field(default=None, description="总内存(字节)")
    used_bytes: int | None = Field(default=None, description="已用内存(字节)")
    available_bytes: int | None = Field(default=None, description="可用内存(字节)")
    usage_percent: float | None = Field(default=None, description="内存使用率(%)")


class DiskStatusOut(BaseModel):
    path: str = Field(..., description="监控路径")
    total_bytes: int | None = Field(default=None, description="总容量(字节)")
    used_bytes: int | None = Field(default=None, description="已用容量(字节)")
    free_bytes: int | None = Field(default=None, description="剩余容量(字节)")
    usage_percent: float | None = Field(default=None, description="磁盘使用率(%)")
    status: str = Field(default="unknown", description="磁盘状态: up/down")


class ServerInfoOut(BaseModel):
    hostname: str | None = Field(default=None, description="主机名")
    os: str | None = Field(default=None, description="操作系统")
    os_release: str | None = Field(default=None, description="系统发行版本")
    machine: str | None = Field(default=None, description="机器架构")
    processor: str | None = Field(default=None, description="CPU 型号")
    app_start_time: datetime = Field(default_factory=datetime.now, description="应用启动时间")


class PythonStatusOut(BaseModel):
    status: str = Field(default="running", description="Python 运行状态")
    version: str | None = Field(default=None, description="Python 版本")
    executable: str | None = Field(default=None, description="Python 可执行路径")
    implementation: str | None = Field(default=None, description="Python 实现")
    process_id: int | None = Field(default=None, description="进程 ID")
    process_cpu_percent: float | None = Field(default=None, description="当前进程 CPU 占比(%)")


class SystemMonitorOut(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.now, description="采样时间")
    app_uptime_seconds: int = Field(default=0, description="应用运行时长(秒)")
    online_users: OnlineUsersOut = Field(default_factory=OnlineUsersOut, description="在线用户监控")
    cpu: CpuStatusOut = Field(default_factory=CpuStatusOut, description="CPU 状态")
    memory: MemoryStatusOut = Field(default_factory=MemoryStatusOut, description="内存状态")
    disk: DiskStatusOut = Field(default_factory=lambda: DiskStatusOut(path="./storage"), description="磁盘状态")
    server: ServerInfoOut = Field(default_factory=ServerInfoOut, description="服务器信息")
    python: PythonStatusOut = Field(default_factory=PythonStatusOut, description="Python 状态")
    services: list[ServiceStatusOut] = Field(default_factory=list, description="服务状态明细")
    services_summary: ServiceSummaryOut = Field(default_factory=ServiceSummaryOut, description="服务汇总")
