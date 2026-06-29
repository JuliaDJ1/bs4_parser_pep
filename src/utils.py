import logging

from bs4 import BeautifulSoup
from requests import RequestException

from constants import EXPECTED_STATUS
from exceptions import ParserFindTagException


def get_response(session, url, encoding='utf-8'):
    try:
        response = session.get(url)
        response.encoding = encoding
        return response
    except RequestException:
        logging.exception(
            f'Возникла ошибка при загрузке страницы {url}',
            stack_info=True
        )


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag


def get_soup(session, url):
    response = get_response(session, url)
    if response is None:
        return None
    return BeautifulSoup(response.text, features='lxml')


def get_pep_status(session, pep_link):
    soup = get_soup(session, pep_link)
    if soup is None:
        return None
    for dt in soup.find_all('dt'):
        if dt.text.strip() in ('Status', 'Status:'):
            dd = dt.find_next_sibling('dd')
            if dd:
                return dd.text.strip()
    return None


def check_status(pep_link, pep_status, preview_status, mismatched):
    expected = EXPECTED_STATUS.get(preview_status, ('Unknown',))
    if pep_status not in expected:
        mismatched.append({
            'url': pep_link,
            'card_status': pep_status,
            'expected': list(expected),
        })


def log_mismatched(mismatched):
    if not mismatched:
        return
    lines = ['\nНесовпадающие статусы:']
    for item in mismatched:
        lines.append(
            '{}\n'
            'Статус в карточке: {}\n'
            'Ожидаемые статусы: {}'.format(
                item['url'],
                item['card_status'],
                item['expected']
            )
        )
    logging.warning('\n'.join(lines))
