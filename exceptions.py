class RequestAPIError(Exception):
    """Исключение для обработки ошибок."""


class HTTPStatusError(Exception):
    """Исключение для обработки ошибок статуса HTTP."""

    def __init__(self, status_code):
        super().__init__(f'Статус: {status_code}')
        self.status_code = status_code
