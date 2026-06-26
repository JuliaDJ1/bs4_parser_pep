# Парсер документации Python и PEP

Парсер собирает данные с официального сайта документации Python и реестра PEP.

## Режимы работы

- **whats-new** — список статей о нововведениях в Python
- **latest-versions** — версии Python и их статусы
- **download** — скачивает архив документации Python (PDF)
- **pep** — статистика по статусам всех PEP-документов с логированием расхождений

## Установка

```bash
git clone https://github.com/JuliaDJ1/bs4_parser_pep.git
cd bs4_parser_pep
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Запуск

```bash
cd src
python main.py <режим> [аргументы]
```

## Технологии

Python 3.9+, BeautifulSoup4, requests-cache, tqdm, prettytable

## Автор

Вадим Гусейнов
