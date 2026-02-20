from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_session
from app.core.errors.exceptions import FileNotFound
from app.core.response import ApiResponse, ok
from app.modules.admin.dao.user import user_crud
from app.modules.admin.models.user import User
from app.modules.admin.services.profile import ProfileService
from app.shared.deps import require_user

profile_router = APIRouter(
    prefix="/user",
    tags=["User - Profile"],
    dependencies=[Depends(require_user)],
)


@profile_router.get("/avatar", summary="获取当前用户头像")
async def get_avatar(current_user: User = Depends(require_user)):
    target, media_type = ProfileService.resolve_avatar_file(current_user.avatar_path)
    if not target:
        raise FileNotFound("头像不存在")
    return FileResponse(path=target, media_type=media_type)


@profile_router.post(
    "/avatar",
    summary="上传当前用户头像",
    response_model=ApiResponse[dict],
)
async def upload_avatar(
    avatar: UploadFile = File(...),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    data = await ProfileService.save_avatar(user=current_user, upload=avatar)
    await user_crud.update(db, current_user)
    return ok(data, message="头像上传成功")
