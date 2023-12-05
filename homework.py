import logging
import os
import sys
import time

import requests
import telegram

import exceptions

from http import HTTPStatus
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания."
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    for token_name, token in {
        "PRACTICUM_TOKEN": PRACTICUM_TOKEN,
        "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID
    }.items():
        if token is None:
            raise exceptions.EnvironmentVariableNotDefined(token_name)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug("Бот успешно отправил сообщение")
    except Exception:
        logger.error("Ошибка при отправке сообщения боту")


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    payload = {"from_date": timestamp}
    response = None
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=payload)
    except Exception as error:
        raise exceptions.EndpointRequestError(error)
    if response.status_code != HTTPStatus.OK:
        raise exceptions.EndpointBadResponse(response.status_code)

    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(response, type(dict))
    if not response.get("current_date"):
        raise exceptions.KeyNotFound("current_date", response)
    if not (homeworks := response.get("homeworks")):
        raise exceptions.KeyNotFound("homeworks", response)
    if not isinstance(homeworks, list):
        raise TypeError(homeworks, type(list))

    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус работы."""
    homework_name = _get_value("homework_name", homework)
    status = _get_value("status", homework)
    if not (verdict := HOMEWORK_VERDICTS.get(status)):
        raise exceptions.UnexpectedStatus(status)
    return f"Изменился статус проверки работы \"{homework_name}\". {verdict}"


def _get_value(key, homework):
    if not (value := homework.get(key)):
        raise exceptions.KeyNotFound(key, homework)
    return value


def _parse_exception(error):
    if isinstance(error, exceptions.EndpointBadResponse):
        code = error.args[0]
        if code == HTTPStatus.NOT_FOUND:
            return (f"Сбой в работе программы: Эндпоинт {ENDPOINT} "
                    "недоступен. Код ответа API: 404")
        elif code == HTTPStatus.UNAUTHORIZED:
            return ("Сбой в работе программы: При запросе к эндпоинту "
                    f"{ENDPOINT} учетные данные не были предоставлены")
        elif code == HTTPStatus.BAD_REQUEST:
            return ("Сбой в работе программы: При запросе к эндпоинту "
                    f"{ENDPOINT} дата предоставлена в неверном формате")
        else:
            return ("Сбой в работе программы: Запрос к эндпоинту "
                    f"{ENDPOINT} вызывал ошибку {code}")
    elif isinstance(error, exceptions.EndpointRequestError):
        return ("Сбой в работе программы: Запрос к эндпоинту "
                f"{ENDPOINT} вызывал ошибку {error}")
    elif isinstance(error, exceptions.KeyNotFound):
        (key, source) = error.args
        return (f"Сбой в работе программы: в объекте {source} "
                f"отсутсвует ключ {key}")
    elif isinstance(error, exceptions.UnexpectedStatus):
        status = error.args[0]
        return (f"Неожиданный статус домашней работы: {status}")
    elif isinstance(error, TypeError):
        (value, expected_type) = error.args
        return f"Объект {value} не соответствует типу {expected_type}"
    else:
        return f"Сбой в работе программы: {error}"


def main():
    """Основная логика работы бота."""
    try:
        check_tokens()
    except exceptions.EnvironmentVariableNotDefined as error:
        logger.critical((
            f"Отсутствует обязательная переменная окружения: \"{error}\""
            "Программа принудительно остановлена"))
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    status = ""
    is_previous_request_ok = True

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logger.debug("Новые статусы отсутствуют")
            else:
                new_status = parse_status(homeworks[0])
                if new_status == status:
                    logger.debug("Новые статусы отсутствуют")
                else:
                    status = new_status
                    send_message(bot, status)
            is_previous_request_ok = True
            timestamp = response.get("current_date")
        except Exception as error:
            message = _parse_exception(error)
            logger.error(message)
            if is_previous_request_ok:
                send_message(bot, message)
            is_previous_request_ok = False
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
