from http import HTTPStatus


class EnvironmentVariableNotDefined(Exception):
    """Отсутствие обязательных переменных окружения."""

    def __init__(self, token):
        """Констуктор."""
        self.token = token

    def __str__(self):
        """Сообщение ошибки."""
        return (
            f"Отсутствует обязательная переменная окружения: \"{self.token}\""
            "Программа принудительно остановлена")


class EndpointBadResponse(Exception):
    """Статус код ответа отличен от 200."""

    def __init__(self, status_code, endpoint):
        """Констуктор."""
        self.status_code = status_code
        self.endpoint = endpoint

    def __str__(self):
        """Сообщение ошибки."""
        if self.status_code == HTTPStatus.NOT_FOUND:
            return (f"Эндпоинт {self.endpoint} "
                    "недоступен. Код ответа API: 404")
        elif self.status_code == HTTPStatus.UNAUTHORIZED:
            return (f"При запросе к эндпоинту {self.endpoint} "
                    "учетные данные не были предоставлены")
        elif self.status_code == HTTPStatus.BAD_REQUEST:
            return (f"При запросе к эндпоинту {self.endpoint} "
                    "дата предоставлена в неверном формате")
        else:
            return (f"Запрос к эндпоинту {self.endpoint} "
                    f"вызывал ошибку {self.status_code}")


class EndpointRequestError(Exception):
    """Сбой при запросе к эндпоинту."""

    def __init__(self, error, endpoint):
        """Констуктор."""
        self.error = error
        self.endpoint = endpoint

    def __str__(self):
        """Сообщение ошибки."""
        return (f"Запрос к эндпоинту {self.endpoint} "
                f"вызывал ошибку {self.error}")


class KeyNotFound(Exception):
    """Отсутствие ожидаемых ключей в ответе API."""

    def __init__(self, key, source):
        """Констуктор."""
        self.key = key
        self.source = source

    def __str__(self):
        """Сообщение ошибки."""
        return f"В объекте {self.source} отсутствует ключ {self.key}"


class UnexpectedStatus(Exception):
    """Неожиданный статус домашней работы, обнаруженный в ответе API."""

    def __init__(self, status):
        """Констуктор."""
        self.status = status

    def __str__(self):
        """Сообщение ошибки."""
        return f"Неожиданный статус домашней работы: {self.status}"
