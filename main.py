#!/usr/bin/env python3
import csv
from urllib import request
from html.parser import HTMLParser


class HTMLTableParser(HTMLParser):
    """ This class serves as a html table parser. It is able to parse multiple
    tables which you feed in. You can access the result per .tables field.
    """

    def __init__(
            self,
            decode_html_entities=False,
            data_separator=' ',
    ):

        HTMLParser.__init__(self)

        self._parse_html_entities = decode_html_entities
        self._data_separator = data_separator

        self._in_td = False
        self._in_th = False
        self._current_table = []
        self._current_row = []
        self._current_cell = []
        self.table = []

    def handle_starttag(self, tag, attrs):
        """ We need to remember the opening point for the content of interest.
        The other tags (<table>, <tr>) are only handled at the closing point.
        """
        if tag == 'td':
            self._in_td = True
        if tag == 'th':
            self._in_th = True

    def handle_data(self, data):
        """ This is where we save content to a cell """
        if self._in_td or self._in_th:
            self._current_cell.append(data.strip())

    def handle_charref(self, name):
        """ Handle HTML encoded characters """

        if self._parse_html_entities:
            self.handle_data(self.unescape('&#{};'.format(name)))

    def handle_endtag(self, tag):
        """ Here we exit the tags. If the closing tag is </tr>, we know that we
        can save our currently parsed cells to the current table as a row and
        prepare for a new row. If the closing tag is </table>, we save the
        current table and prepare for a new one.
        """
        if tag == 'td':
            self._in_td = False
        elif tag == 'th':
            self._in_th = False

        if tag in ['td', 'th']:
            final_cell = self._data_separator.join(self._current_cell).strip()
            self._current_row.append(final_cell)
            self._current_cell = []
        elif tag == 'tr':
            self._current_table.append(self._current_row)
            self._current_row = []
        elif tag == 'table':
            self.table += self._current_table
            self._current_table = []


def get_input_data():
    result = []
    with open('input.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            r = {
                    'ip': row['ip'],
                    'login': row['login'],
                    'password': row['password'],
                }
            result.append(r)
    return result


def get_html(ip, login, password):
    url = 'http://' + ip + '/control/camerainfo'
    p = request.HTTPPasswordMgrWithDefaultRealm()
    p.add_password(None, url, login, password);

    auth_handler = request.HTTPBasicAuthHandler(p)

    opener = request.build_opener(auth_handler)

    request.install_opener(opener)

    html = ''

    result = opener.open(url)
    html = result.read()

    return html


def process_item(item):
    html = get_html(item['ip'], item['login'], item['password'])
    result = {
        'ip': item['ip'],
    }
    if not html:
        return result
    html = html.decode('utf-8')
    p = HTMLTableParser()
    p.feed(html)

    try:
        t = p.table
    except IndexError as e:
        print(html)
        raise e
    last_title = ''
    for r in t:
        title = r[0]
        if len(r) < 2:
            continue
        # hack 'Listening Ports'
        if title == 'Listening Ports':
            if 'Listening Ports' not in result:
                result['Listening Ports'] = []
            result['Listening Ports'].append(r[1] + ' ' + r[2])
        elif not title and last_title == 'Listening Ports':
            title = 'Listening Ports'
            result['Listening Ports'].append(r[1]+' '+r[2])
        else:
            result[title] = r[1]
        last_title = title
    result['Listening Ports'] = '"%s"' % '\r\n'.join(result['Listening Ports'])
    result['status'] = 'OK'
    return result


def process_list(l):
    result = []
    for item in l:
        print('Processing %s' % item['ip'])
        try:
            r = process_item(item)
            if r:
                result.append(r)
        except IOError as e:
            print("IO error '%s' while trying to process IP: %s" % (e, item['ip']))
            result.append({'ip':item['ip'], 'status': 'IO ERROR: %s' % e})
        except BaseException as e:
            print("Unknown error '%s' while trying to process IP: %s" % (e, item['ip']))
            raise e
    return result


def main():
    result = process_list(get_input_data())
    if result:
        with open('output.csv', 'w') as csvfile:
            keys = []
            for n in result:
                keys += list(n.keys())
            keys = list(set(keys))
            keys.pop(keys.index('ip'))
            fieldnames = ['ip', 'status']+keys
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for r in result:
                writer.writerow(r)
            print("Success: %s" % r['ip'])
    else:
        print('No result data')


if __name__ == "__main__":
    main()
