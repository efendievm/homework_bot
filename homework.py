import logging
import os
import sys
import time

import requests
import telegram

import exceptions

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    for token_name, token in {
        "PRACTICUM_TOKEN": PRACTICUM_TOKEN,
        "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID
    }.items():
        if token is None:
            raise exceptions.OsVariableNotDefined(token_name)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f"Бот отправил сообщение \"{message}\"")
    except Exception:
        logger.error(f"Сбой при отправке сообщения \"{message}\"")


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    url = ENDPOINT
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': timestamp}
    response = None
    try:
        response = requests.get(url, headers=headers, params=payload)
    except Exception as error:
        message = ("Сбой в работе программы: Запрос к эндпоинту "
                   f"{ENDPOINT} вызывал ошибку {error}")
        raise exceptions.EndpointRequestError(message)

    if response.status_code == 404:
        message = (f"Сбой в работе программы: Эндпоинт {ENDPOINT} "
                   "недоступен. Код ответа API: 404")
        raise exceptions.EndpointNotAvailable(message)
    elif response.status_code == 401:
        message = ("Сбой в работе программы: При запросе к эндпоинту "
                   f"{ENDPOINT} учетные данные не были предоставлены")
        raise exceptions.EndpointRequestError(message)
    elif response.status_code == 400:
        message = ("Сбой в работе программы: При запросе к эндпоинту "
                   f"{ENDPOINT} дата предоставлена в неверном формате")
        raise exceptions.EndpointRequestError(message)
    elif response.status_code != 200:
        message = ("Сбой в работе программы: Запрос к эндпоинту "
                   f"{ENDPOINT} вызывал ошибку {response.status_code}")
        raise exceptions.EndpointRequestError(message)

    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(response)
    homeworks = response.get("homeworks")
    if homeworks is None:
        raise exceptions.KeyNotFound("homeworks")
    if not isinstance(homeworks, list):
        raise TypeError(homeworks)

    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус работы."""
    def get_value(key):
        value = homework.get(key)
        if homework.get(key) is None:
            raise exceptions.KeyNotFound(key)
        return value
    homework_name = get_value("homework_name")
    status = get_value("status")
    verdict = HOMEWORK_VERDICTS.get(status)
    if verdict is None:
        raise exceptions.UnexpectedStatus(status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def _parse_statuses(response, homeworks):
    statuses = []
    for homework in response:
        message = parse_status(homework)
        (homework_name, verdict) = message.split(
            "Изменился статус проверки работы \"")[1].split("\".")
        if homework_name not in homeworks:
            statuses.append(message)
        elif homeworks[homework_name] != verdict:
            statuses.append(message)
        homeworks[homework_name] = verdict
    return statuses


def _log_error_and_send_message(bot, message, is_previous_request_ok):
    logger.error(message)
    if is_previous_request_ok:
        send_message(bot, message)


def main():
    """Основная логика работы бота."""
    try:
        check_tokens()
    except exceptions.OsVariableNotDefined as error:
        logger.critical((
            f"Отсутствует обязательная переменная окружения: '{error}'"
            "Программа принудительно остановлена"))
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    is_previous_request_ok = True
    homeworks = {}

    while True:
        try:
            timestamp = int(time.time())
            response = get_api_answer(timestamp)
            response = check_response(response)
            statuses = _parse_statuses(response, homeworks)
            is_previous_request_ok = True
            for status in statuses:
                send_message(bot, status)
            if len(statuses) == 0:
                logger.debug("Новые статусы отсутствуют")
        except (exceptions.EndpointNotAvailable,
                exceptions.EndpointRequestError,
                exceptions.KeyNotFound,
                exceptions.UnexpectedStatus,
                TypeError) as error:
            _log_error_and_send_message(bot, error, is_previous_request_ok)
            is_previous_request_ok = False
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            _log_error_and_send_message(bot, message, is_previous_request_ok)
            is_previous_request_ok = False
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
