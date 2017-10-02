*** Settings ***

Documentation  A test suite with a tests for insider tender auction.
Suite setup       Отримати вхідні дані
Suite teardown    Close all browsers
Resource       resource.robot

*** Test Cases ***
Перевірка логіну
    Долучитись до аукціону 1 учасником
    Долучитись до аукціону 2 учасником

Очікування початку голландської частини аукціону
    Дочекатистись паузи до Голландського етапу
    Перевірити інформацію про тендер
    Дочекатистись завершення паузи перед Голландського етапом

Голландський аукціон
    Долучитись до аукціону 3 учасником
    Зробити заявку
    Долучитись до аукціону 4 учасником

Очікування початку Sealed Bid етапу
    Дочекатистись паузи до Sealed Bid етапу
    Дочекатистись завершення паузи перед Sealed Bid етапом

Проведення Sealed Bid частини аукціону
    Долучитись до аукціону глядачем
    Долучитись до аукціону 5 учасником
    Спробувати зробити надто низьку ставку
    Переключитись на 1 учасника
    Зробити ставку
    Відредагувати ставку
    Відмінитити ставку
    Переключитись на 2 учасника
    Зробити ставку
    Переключитись на 4 учасника
    Зробити ставку

Очікування початку Best Bid етапу
    Дочекатистись паузи до Best Bid етапу
    Дочекатистись завершення паузи перед Best Bid етапом

Проведення Bestbid частини аукціону
    Переключитись на 3 учасника
    Спробувати зробити невалідну ставку переможцем голландської частини
    Підвищити пропозицію переможцем голландської частини

Завершення аукціону
    Дочекатистись завершення аукціону