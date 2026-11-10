"""Private URL validation shared by game and standalone room relay."""
import ipaddress
from urllib.parse import urlsplit

def private_url(url):
    p = urlsplit(url)
    if p.scheme not in {'http', 'https'} or p.username or p.password or p.query or p.fragment:
        raise ValueError('A private HTTP(S) URL is required')
    host = p.hostname or ''
    if host in {'localhost', '::1'} or host.endswith('.ts.net'):
        return url.rstrip('/')
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private and not ip.is_unspecified and not ip.is_multicast:
            return url.rstrip('/')
    except ValueError:
        pass
    raise ValueError('Only loopback, private LAN or tailnet URLs are allowed')

