from pathlib import Path


BASE_DIR = Path(__file__).parent
RESULTS_DIR = BASE_DIR / 'results'
DOWNLOADS_DIR = BASE_DIR / 'downloads'

MAIN_DOC_URL = 'https://docs.python.org/3/'
PEP_URL = 'https://peps.python.org/'

DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'
DT_FORMAT = '%d.%m.%Y %H:%M:%S'
LOG_FORMAT = '"%(asctime)s - [%(levelname)s] - %(message)s"'
LOG_DIR = 'logs'
LOG_FILE = 'parser.log'
LOG_MAX_BYTES = 10 ** 6
LOG_BACKUP_COUNT = 5

EXPECTED_STATUS = {
    'A': ('Active', 'Accepted'),
    'D': ('Deferred',),
    'F': ('Final',),
    'P': ('Provisional',),
    'R': ('Rejected',),
    'S': ('Superseded',),
    'W': ('Withdrawn',),
    '': ('Draft', 'Active'),
}
