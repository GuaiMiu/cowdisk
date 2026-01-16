"""
@File: base.py
@Author: GuaiMiu
@Date: 2025/3/18 11:31
@Version: 1.0
@Description:
"""

from datetime import datetime
from typing import Type, TypeVar, Generic, Optional, Any, Sequence

from fastapi_pagination import Params
from fastapi_pagination.ext.sqlmodel import apaginate
from sqlalchemy.sql import Select
from sqlmodel import SQLModel, select, or_
from sqlmodel.ext.asyncio.session import AsyncSession

T = TypeVar("T", bound=SQLModel)


class CurdBase(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

    async def create(self, db: AsyncSession, obj: T) -> T:
        """
        创建数据
        :param db:
        :param obj:
        :return:
        """
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def get_by_id(self, db: AsyncSession, obj_id: int) -> T:
        """
        通过 ID 获取数据
        :param db:
        :param obj_id:
        :return:
        """
        obj = await db.get(self.model, obj_id)
        return obj

    async def get_all(
        self, db: AsyncSession, params: Params | None = None
    ) -> Sequence[T] | dict:
        """
        获取所有数据
        :param params: 分页参数 可选
        :param db:
        :return:
        """
        statement: Select = select(self.model).where(
            getattr(self.model, "is_deleted") == False
        )
        if params:
            result = await apaginate(db, statement, params)
            return result
        result = await db.exec(statement)
        return result.all()

    async def get_all_by_field(
        self, db: AsyncSession, field_name: str, field_value: Any
    ) -> Sequence[T]:
        """
        通过指定字段和其对应的值来查询数据
        :param db:
        :param field_name:
        :param field_value:
        :return:
        """
        field = getattr(self.model, field_name)
        statement: Select = select(self.model).where(field == field_value)
        result = await db.exec(statement)
        return result.all()

    async def get_all_by_fields(
        self, db: AsyncSession, fields: dict[str, Any]
    ) -> Sequence[T]:
        """
        通过指定多个字段和其对应的值来查询数据
        :param db:
        :param fields:
        :return:
        """
        statement = select(self.model)
        for field_name, field_value in fields.items():
            field = getattr(self.model, field_name)
            statement = statement.where(field == field_value)
        result = await db.exec(statement)
        return result.all()

    async def get_all_by_ids(self, db: AsyncSession, ids: list[int]):
        """
        通过指定多个 ID 来查询数据
        :param db:
        :param ids:
        :return:
        """
        statement: Select = select(self.model).where(getattr(self.model, "id").in_(ids))
        result = await db.exec(statement)
        return result.all()

    async def update(self, db: AsyncSession, obj: SQLModel) -> T:
        """
        更新指定 ID 的数据
        :param db:
        :param obj:
        :return:
        """
        obj.sqlmodel_update(obj)
        if obj.update_time:
            obj.update_time = datetime.now()
        await db.commit()
        await db.refresh(obj)
        return obj

    async def delete(self, db: AsyncSession, obj_id: int) -> bool:
        """
        删除指定 ID 的数据
        :param db:
        :param obj_id:
        :return:
        """
        obj = await db.get(self.model, obj_id)
        if obj:
            # await db.delete(obj)
            obj.is_deleted = True
            await db.commit()
            return True
        return False

    async def get_by_field(
        self, db: AsyncSession, field_name: str, field_value: Any
    ) -> Optional[T]:
        """
        通过指定字段和其对应的值来查询数据
        :param db: 异步数据库会话
        :param field_name: 字段名
        :param field_value: 字段值
        :return: 匹配的对象，如果没有匹配则返回 None
        """
        field = getattr(self.model, field_name)
        statement: Select = select(self.model).where(field == field_value)
        result = await db.exec(statement)
        return result.first()

    async def is_exist_by_field(
        self, db: AsyncSession, field_name: str, field_value: Any
    ) -> bool:
        """
        通过指定字段和其对应的值来查询数据是否存在
        :param db:
        :param field_name:
        :param field_value:
        :return:
        """
        field = getattr(self.model, field_name)
        statement: Select = select(self.model).where(field == field_value)
        result = await db.exec(statement)
        return result.first() is not None

    async def get_by_or_fields(
        self, db: AsyncSession, fields: list[str], values: Any
    ) -> Optional[T]:
        """
        通过指定多个字段和其对应的值来查询数据
        :param values:
        :param db:
        :param fields:
        :return:
        """
        statement = select(self.model)
        conditions = []

        for field_name in fields:
            field_value = getattr(values, field_name)
            field = getattr(self.model, field_name)
            conditions.append(field == field_value)
        statement: Select = statement.where(or_(*conditions))
        result = await db.exec(statement)
        obj = result.first()
        if obj:
            if hasattr(values, "id") and obj.id == values.id:
                return None
            return obj
        return None
