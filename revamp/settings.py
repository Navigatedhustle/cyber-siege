"""Local-only configuration; no inference endpoint or network settings are changed."""
import os
from pathlib import Path
from urllib.parse import urlsplit
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv('SIEGE_DATA', str(ROOT / 'runtime/revamp'))).resolve()
PORT = int(os.getenv('SIEGE_PORT', '8090'))
BASE = os.getenv('SIEGE_BASE_URL', f'http://127.0.0.1:{PORT}').rstrip('/')
SCALE = float(os.getenv('SIEGE_TIME_SCALE', '1'))
if not .005 <= SCALE <= 1:
    raise ValueError('SIEGE_TIME_SCALE must be between .005 and 1')

from .private import private_url

private_url(BASE)
config = yaml.safe_load((ROOT / 'models.yaml').read_text())['models']['hero']
MODEL = config['model_id']
MODEL_URL = os.getenv('SIEGE_TEST_MODEL_URL', config['base_url'])
if urlsplit(MODEL_URL).hostname not in {'127.0.0.1', 'localhost', '::1'}:
    raise ValueError('Model requests must remain on loopback')
