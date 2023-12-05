class EnvironmentVariableNotDefined(Exception):
    """Отсутствие обязательных переменных окружения."""

    pass


class EndpointBadResponse(Exception):
    """Статус код ответа отличен от 200."""

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
