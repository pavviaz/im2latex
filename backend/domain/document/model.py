import enum


class ShareRoleEnum(enum.Enum):
    private = "закрытый доступ"
    viewer = "только просмотр"
    edit = "редактирование"
