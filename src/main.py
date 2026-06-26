import logging
import re
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import (
    BASE_DIR,
    MAIN_DOC_URL,
    PEP_URL,
    EXPECTED_STATUS,
)
from outputs import control_output
from utils import get_response, find_tag


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    main_div = find_tag(
        soup, 'section', attrs={'id': 'what-s-new-in-python'}
    )
    div_with_url = find_tag(
        main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_url.find_all(
        'li', attrs={'class': 'toctree-l1'})
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = find_tag(section, 'a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, features='lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append((version_link, h1.text, dl_text))
    return results


def latest_versions(session):
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise Exception('Nothing found')
    results = [('Link', 'Version', 'Status')]
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
    response = get_response(session, downloads_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    main_tag = find_tag(soup, 'div', attrs={'role': 'main'})
    table_tag = find_tag(main_tag, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = table_tag.find(
        'a',
        attrs={'href': re.compile(r'.+pdf-a4\.zip$')}
    )
    if pdf_a4_tag is None:
        pdf_a4_tag = table_tag.find(
            'a', attrs={'href': re.compile(r'.+\.zip$')})
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
    logging.info(f'Archive saved: {archive_path}')


def get_pep_status(session, pep_link):
    pep_response = get_response(session, pep_link)
    if pep_response is None:
        return None
    pep_soup = BeautifulSoup(pep_response.text, features='lxml')
    for dt in pep_soup.find_all('dt'):
        if dt.text.strip() == 'Status':
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
    lines = ['Mismatched statuses:']
    for item in mismatched:
        lines.append(
            f"{item['url']}\n"
            f"Status in card: {item['card_status']}\n"
            f"Expected: {item['expected']}"
        )
    logging.warning('\n'.join(lines))


def pep(session):
    response = get_response(session, PEP_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
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
    results = [('Status', 'Quantity')]
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
    logging.info('Parser started!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'CLI args: {args}')
    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        control_output(results, args)
    logging.info('Parser finished.')


if __name__ == '__main__':
    main()
