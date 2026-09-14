"""Read a link listing from an external site.

Shared by any feature that needs an external listing. Nothing here names a
particular site: every address and every markup hook arrives in a source
mapping, so pointing the crawler at another listing is a settings change rather
than a code change. See `POLICY_SOURCE` in settings for the shape.

Required source keys:
    base_url, list_path   the listing address, joined
    table_class           class on the table holding the listing
    cell_class            class on the cells holding the links
    limit                 how many links to keep
    timeout, user_agent, max_bytes

No function here raises. A site that is down, slow, or restructured has to
leave the page working, so every failure comes back as a message to display.
"""
from urllib.error import URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

NETWORK_ERROR = '외부 자료를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.'
MARKUP_ERROR = '외부 목록의 구조가 바뀌어 항목을 읽지 못했습니다. 원문에서 확인해 주세요.'

# The stdlib backend keeps the crawler free of a compiled dependency and is
# comfortably fast for a listing page.
PARSER = 'html.parser'


def list_url(source):
    """The full address of the listing page."""
    return urljoin(source['base_url'], source['list_path'])


def fetch(source):
    """Return the listing HTML, or an empty string and a message on failure."""
    url = list_url(source)
    if urlsplit(url).scheme not in ('http', 'https'):
        return '', NETWORK_ERROR
    request = Request(url, headers={'User-Agent': source['user_agent'],
                                    'Accept': 'text/html'})
    try:
        with urlopen(request, timeout=source['timeout']) as response:
            if getattr(response, 'status', 200) != 200:
                return '', NETWORK_ERROR
            charset = response.headers.get_content_charset() or 'utf-8'
            # Capped so an unexpectedly large or endless response cannot tie up
            # the request that is only meant to fill a dialog.
            return response.read(source['max_bytes']).decode(charset, 'replace'), ''
    except (URLError, OSError, ValueError, UnicodeError):
        return '', NETWORK_ERROR


def parse_links(markup, source):
    """Read title/url pairs out of the listing table, dropping anything off-site.

    A relative href resolves against the configured base. Anything that lands
    on another host is discarded rather than shown, so a change on the source
    page cannot put an unrelated link in front of the reader.
    """
    table = BeautifulSoup(markup, PARSER).find('table', class_=source['table_class'])
    if table is None:
        return []
    host = urlsplit(source['base_url']).netloc
    items = []
    for cell in table.find_all('td', class_=source['cell_class']):
        for anchor in cell.find_all('a'):
            title = (anchor.get('title') or '').strip()
            href = (anchor.get('href') or '').strip()
            if not title or not href:
                continue
            url = urljoin(source['base_url'], href)
            split = urlsplit(url)
            if split.scheme in ('http', 'https') and split.netloc == host:
                items.append({'title': title, 'url': url})
                if len(items) >= source['limit']:
                    return items
    return items


def crawl(source):
    """Fetch and parse in one call. Always returns a result, never raises."""
    markup, error = fetch(source)
    if error:
        return [], error
    items = parse_links(markup, source)
    return (items, '') if items else ([], MARKUP_ERROR)
