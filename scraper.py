import requests
import io
from bs4 import BeautifulSoup
import sys
import re
RESTAURAUNT_DICT = {}

INSPECTION_DOMAIN = 'http://info.kingcounty.gov'
INSPECTION_PATH = '/health/ehs/foodsafety/inspections/Results.aspx'
INSPECTION_PARAMS = {
    'Output': 'W',
    'Business_Name': '',
    'Business_Address': '',
    'Longitude': '',
    'Latitude': '',
    'City': '',
    'Zip_Code': '',
    'Inspection_Type': 'All',
    'Inspection_Start': '',
    'Inspection_End': '',
    'Inspection_Closed_Business': 'A',
    'Violation_Points': '',
    'Violation_Red_Points': '',
    'Violation_Descr': '',
    'Fuzzy_Search': 'N',
    'Sort': 'H'
}


def get_inspection_page(**kwargs):
    """Get data and write to file."""
    url = INSPECTION_DOMAIN + INSPECTION_PATH
    params = INSPECTION_PARAMS.copy()
    for key, val in kwargs.items():
        if key in INSPECTION_PARAMS:
            params[key] = val
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    open_file = io.open("inspection.html", "wb")
    open_file.truncate()
    open_file.write(resp.content)
    open_file.close()
    return resp.content


def load_inspection_page(file):
    """Open file with data."""
    open_file = io.open(file, "r")
    read_file = open_file.read()
    open_file.close()
    return read_file


def parse_source(html):
    """Run beautiful soup on data."""
    parsed = BeautifulSoup(html, 'html5lib')
    return parsed


def has_two_tds(elem):
    """Start extracting data."""
    is_tr = elem.name == 'tr'
    td_children = elem.find_all('td', recursive=False)
    has_two = len(td_children) == 2
    return is_tr and has_two


def extract_data_listings(html):
    """Extract data listings."""
    id_finder = re.compile(r'PR[\d]+~')
    return html.find_all('div', id=id_finder)


def clean_data(td):
    """Clean up data."""
    data = td.string
    try:
        return data.strip(" \n:-")
    except AttributeError:
        return u""


def extract_restaurant_metadata(elem):
    """Extract metadata."""
    metadata_rows = elem.find('tbody').find_all(
        has_two_tds, recursive=False
    )
    rdata = {}
    current_label = ''
    for row in metadata_rows:
        key_cell, val_cell = row.find_all('td', recursive=False)
        new_label = clean_data(key_cell)
        current_label = new_label if new_label else current_label
        rdata.setdefault(current_label, []).append(clean_data(val_cell))
    return rdata


def is_inspection_row(elem):
    """Find inspection details for restauraunt."""
    is_tr = elem.name == 'tr'
    if not is_tr:
        return False
    td_children = elem.find_all('td', recursive=False)
    has_four = len(td_children) == 4
    this_text = clean_data(td_children[0]).lower()
    contains_word = 'inspection' in this_text
    does_not_start = not this_text.startswith('inspection')
    return is_tr and has_four and contains_word and does_not_start


def extract_score_data(elem):
    """Get inspection score."""
    inspection_rows = elem.find_all(is_inspection_row)
    samples = len(inspection_rows)
    total = high_score = average = 0
    for row in inspection_rows:
        strval = clean_data(row.find_all('td')[2])
        try:
            intval = int(strval)
        except (ValueError, TypeError):
            samples -= 1
        else:
            total += intval
            high_score = intval if intval > high_score else high_score
    if samples:
        average = total / float(samples)
    data = {
        u'Average Score': average,
        u'High Score': high_score,
        u'Total Inspections': samples
    }
    return data

if __name__ == '__main__':
    kwargs = {
        'Inspection_Start': '2/1/2013',
        'Inspection_End': '2/1/2015',
        'Zip_Code': '98109'
    }
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        html = load_inspection_page('inspection.html')
    else:
        html = get_inspection_page(**kwargs)
    doc = parse_source(html)
    listings = extract_data_listings(doc)
    for listing in listings:
        metadata = extract_restaurant_metadata(listing)
        score_data = extract_score_data(listing)
        print(metadata.get('Business Name'))
        print(score_data)
        RESTAURAUNT_DICT[metadata.get('Business Name')[0]] = "# of inspections: " + str(score_data.get('Total Inspections')), "Average Score: " + str(score_data.get('Average Score')), "High Score: " + str(score_data.get('High Score'))
    print(RESTAURAUNT_DICT)


