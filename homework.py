import os
import sys
import time
import logging
from http import HTTPStatus
import requests
from dotenv import load_dotenv
from telebot import TeleBot
from exceptions import MyException

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKENENV')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKENENV')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID_ENV')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    token_list = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ]
    return all(token_list)


def send_message(bot, message):
    """Отправка сообщений в Telegram-чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено {message}')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервисса."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        response.raise_for_status()
        if response.status_code != HTTPStatus.OK:
            logging.error(
                f'Статус ответа'
                f'{response.status_code}')
            raise requests.HTTPError(f'Статус {response.status_code}')
        return response.json()
    except Exception as request_error:
        logging.error(f'Ошибка при запросе к API: {request_error}')
        raise MyException(f'Ошибка при запросе к API: {request_error}')


def check_response(response):
    """Проверяет ответ API на соответствие формату."""
    if not response:
        raise ValueError('Содержит пустой словарь.')
    if not isinstance(response, dict):
        raise TypeError('Не является словарем.')
    if 'homeworks' not in response:
        raise KeyError('Ключа "homeworks" нет в response.')
    if 'current_date' not in response:
        raise KeyError('Ключа "current_date" нет в response.')
    if not isinstance(response['homeworks'], list):
        raise TypeError('В словаре не список.')
    return response['homeworks']


def parse_status(homework):
    """Извлекает статус конкретной домашней работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name"')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ status')
    if not verdict:
        raise ValueError(f'Неизвестный статус работы: {status}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Не хватает переменных окружения.')
        sys.exit(1)

    bot = TeleBot(token=TELEGRAM_TOKEN)
    # Временная метка (далее: В.М.) для отслеживания времени
    # последних изменений в API.
    timestamp = int(time.time())

    while True:
        try:
            # Делаем запрос к API с В.М., чтобы получить данные о ДЗ
            # обновленные после В.М.
            response = get_api_answer(timestamp)
            # Проверка на корректность, выгрузка списка ДЗ
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
                logging.debug('Новый статус отправлен.')
            else:
                logging.debug('Новых уведомлений нет.')
            # Обновляем временную метку
            timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        # Запросы каждые 10 минут
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    # Настройка базовой конфигурации модуля logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    main()
