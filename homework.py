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
        raise exceptions.EndpointBadResponse(response.status_code, ENDPOINT)

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


def main():
    """Основная логика работы бота."""
    try:
        check_tokens()
    except exceptions.EnvironmentVariableNotDefined as error:
        logger.critical(error)
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    status = ""
    is_previous_request_ok = True

    while True:
        error_message = ""
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            is_previous_request_ok = True
            timestamp = response.get("current_date", timestamp)
            if len(homeworks) == 0:
                logger.debug("Новые статусы отсутствуют")
                continue
            new_status = parse_status(homeworks[0])
            if new_status == status:
                logger.debug("Новые статусы отсутствуют")
                continue
            status = new_status
            send_message(bot, status)
            logger.debug(status)
        except TypeError as error:
            (value, expected_type) = error.args
            error_message = (f"Объект {value} не соответствует "
                             f"типу {expected_type}")
        except Exception as error:
            error_message = error
        finally:
            if error_message != "":
                logger.error(error_message)
                if is_previous_request_ok:
                    send_message(bot, error_message)
                is_previous_request_ok = False
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
