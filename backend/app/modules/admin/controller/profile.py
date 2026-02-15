from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_async_session
from app.modules.admin.dao.user import user_crud
from app.modules.admin.models.response import ResponseModel
from app.modules.admin.models.user import User
from app.modules.admin.services.profile import ProfileService
from app.shared.deps import require_user
from app.utils.response import Res

profile_router = APIRouter(
    prefix="/user",
    tags=["User - Profile"],
    dependencies=[Depends(require_user)],
)


@profile_router.get("/avatar", summary="获取当前用户头像")
async def get_avatar(current_user: User = Depends(require_user)):
    target, media_type = ProfileService.resolve_avatar_file(current_user.avatar_path)
    if not target:
        raise HTTPException(status_code=404, detail="头像不存在")
    return FileResponse(path=target, media_type=media_type)


@profile_router.post(
    "/avatar",
    summary="上传当前用户头像",
    response_model=ResponseModel[dict],
)
async def upload_avatar(
    avatar: UploadFile = File(...),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_async_session),
):
    data = await ProfileService.save_avatar(user=current_user, upload=avatar)
    await user_crud.update(db, current_user)
    return Res.success(data=data, msg="头像上传成功")
