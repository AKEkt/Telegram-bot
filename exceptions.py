class NotListException(Exception):
    """Исключение ответ не список."""

    pass


class StatusCodeException(Exception):
    """Исключение код ответа API не 200."""

    pass


class NotStatusException(Exception):
    """Исключение нет статуса домашней работы."""

    pass


class EmptyListException(Exception):
    """Исключение пустой список домашней работы."""

    pass


class TelegMessException(Exception):
    """Исключение пустой список домашней работы."""

    pass
