class OsVariableNotDefined(Exception):
    """Отсутствие обязательных переменных окружения."""

    pass


class EndpointNotAvailable(Exception):
    """Недоступность эндпоинта."""

    pass


class EndpointRequestError(Exception):
    """Сбой при запросе к эндпоинту."""

    pass


class KeyNotFound(Exception):
    """Отсутствие ожидаемых ключей в ответе API."""

    pass


class UnexpectedStatus(Exception):
    """Неожиданный статус домашней работы, обнаруженный в ответе API."""

    pass
