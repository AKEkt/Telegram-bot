import logging
import os
import sys
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (EmptyListException, NotListException,
                        NotStatusException, StatusCodeException,
                        TelegMessException)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('my_log_bot.log', maxBytes=50000000, backupCount=5)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Бот отправил сообщение: {message}')
    except telegram.error.TelegramError as err:
        raise telegram.error.TelegramError(
            f'Сбой при отправке сообщения в Telegram: {err}'
        )
    except Exception as err:
        raise TelegMessException(
            f'Сообщение в Telegram не отправлено по причине: {err}'
        )


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    get_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    try:
        homework_statuses = requests.get(**get_params)
    except requests.ConnectionError as err:
        raise requests.ConnectionError(f'Сбой в запросе к API-сервису: {err}.')
    if homework_statuses.status_code != HTTPStatus.OK:
        message = (
            f'Запрос к эндпоинту: {ENDPOINT}'
            f' с времянной меткой: {timestamp}.'
            f' В ответе получен заголовок сервера:'
            f' {homework_statuses.headers.get("content-type")}.'
            f' Код ответа API: {homework_statuses.status_code}'
            f' Эндпоинт с url: {homework_statuses.url} недоступен!'
        )
        raise StatusCodeException(message)
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    try:
        answer = response['homeworks']
    except KeyError as err:
        raise KeyError(f'Ответ не содержит ключа: {err}')
    if not isinstance(answer, list):
        raise NotListException('Ответ от API приходят не в виде списка.')
    if not answer:
        raise EmptyListException('Cписок домашних работ - пуст!')
    return answer


def parse_status(homework):
    """Статус домашней работы."""
    try:
        homework_status = homework['status']
        homework_name = homework['homework_name']
    except KeyError as err:
        raise KeyError(f'Ответ не содержит ключа: {err}.')
    if homework_status == '':
        raise NotStatusException('Недокументированный статус домашней работы.')
    for status, message in HOMEWORK_STATUSES.items():
        if status == homework_status:
            verdict = message
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    current_timestamp = int(time.time())
    message = 'Старт!'
    bot_message_on = True
    message_old = ''
    status_old = ''
    if not check_tokens():
        logging.critical(
            'Работа программы прекращена!'
            ' Отсутствие одной из обязательных переменных окружения.'
        )
        sys.exit()
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Бот отправил сообщение: "{message}"')
    except Exception as err:
        logging.critical(
            f'Работа программы прекращена! Неверный токен: {err}'
        )
        sys.exit()

    message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            list_homework = check_response(response)
            message_status = parse_status(list_homework[0])
            send_message(bot, message_status)
            current_timestamp = response.get('current_date')
        except (requests.ConnectionError,
                StatusCodeException,
                NotListException,
                EmptyListException,
                NotStatusException,
                KeyError) as err:
            message = f'{err}'
            logging.error(message)
            bot_message_on = True
        except (telegram.error.TelegramError,
                TelegMessException) as err:
            message = f'{err}'
            logging.error(message)
            bot_message_on = False
        except Exception as err:
            message = f'Сбой в работе программы: {err}'
            logging.error(message)
            bot_message_on = False
        else:
            if message_status == status_old:
                logging.debug('В ответе нет новых статусов!')
            status_old = message_status
        finally:
            if message != message_old and bot_message_on:
                message_old = message
                send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
