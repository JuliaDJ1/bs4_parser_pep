import logging
import re
from urllib.parse import urljoin

import requests_cache
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, MAIN_DOC_URL, PEP_URL
from exceptions import ParserFindTagException
from outputs import control_output
from utils import (
    find_tag,
    get_soup,
    get_pep_status,
    check_status,
    log_mismatched,
)


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    soup = get_soup(session, whats_new_url)
    if soup is None:
        return
    main_div = find_tag(
        soup, 'section', attrs={'id': 'what-s-new-in-python'}
    )
    div_with_url = find_tag(
        main_div, 'div', attrs={'class': 'toctree-wrapper'}
    )
    sections_by_python = div_with_url.find_all(
        'li', attrs={'class': 'toctree-l1'}
    )
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = find_tag(section, 'a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        soup = get_soup(session, version_link)
        if soup is None:
            continue
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append((version_link, h1.text, dl_text))
    return results


def latest_versions(session):
    soup = get_soup(session, MAIN_DOC_URL)
    if soup is None:
        return
    sidebar = find_tag(
        soup, 'div', attrs={'class': 'sphinxsidebarwrapper'}
    )
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise ParserFindTagException('Не найден список версий Python')
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append((link, version, status))
    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    soup = get_soup(session, downloads_url)
    if soup is None:
        return
    main_tag = find_tag(soup, 'div', attrs={'role': 'main'})
    table_tag = find_tag(
        main_tag, 'table', attrs={'class': 'docutils'}
    )
    pdf_a4_tag = table_tag.find(
        'a', attrs={'href': re.compile(r'.+pdf-a4\.zip$')}
    )
    if pdf_a4_tag is None:
        pdf_a4_tag = table_tag.find(
            'a', attrs={'href': re.compile(r'.+\.zip$')}
        )
    if pdf_a4_tag is None:
        logging.error('PDF archive link not found')
        return
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(f'Архив сохранён: {archive_path}')


def pep(session):
    soup = get_soup(session, PEP_URL)
    if soup is None:
        return
    tables = soup.find_all('table', attrs={'class': 'pep-zero-table'})
    rows = []
    for table in tables:
        rows.extend(table.find_all('tr'))
    status_count = {}
    mismatched = []
    for row in tqdm(rows):
        cols = row.find_all('td')
        if not cols:
            continue
        preview_status = cols[0].text.strip()[1:]
        a_tag = cols[1].find('a')
        if a_tag is None:
            continue
        if cols[1].text.strip() == '0':
            continue
        pep_link = urljoin(PEP_URL, a_tag['href'])
        pep_status = get_pep_status(session, pep_link)
        if pep_status is None:
            continue
        check_status(pep_link, pep_status, preview_status, mismatched)
        status_count[pep_status] = status_count.get(pep_status, 0) + 1
    log_mismatched(mismatched)
    results = [('Статус', 'Количество')]
    results.extend(status_count.items())
    results.append(('Total', sum(status_count.values())))
    return results


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    logging.info('Парсер запущен!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы: {args}')
    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        control_output(results, args)
    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
