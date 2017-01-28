#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET
import cerberus
import schema


#define output files
OSM_PATH = "las-vegas_nevada.osm"
NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
STATES = ['AZ','NV','CA']
SCHEMA = schema.schema


street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)


ROAD_NAME_EXPECTED = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road",
            "Trail", "Parkway", "Commons","Highway","Way","Circle","North","South","East","West","Apache"]

# UPDATE THIS VARIABLE
ROAD_NAME_MAPPING = {"St": "Street",
            "St.": "Street",
            "Ave": "Avenue",
            "Ave.": "Avenue",
            "ave": "Avenue",
            "AVE": "Avenue",
            "Rd.": "Road",
            "Rd": "Road",
            "Blvd.":"Boulevard",
            "Blvd":"Boulevard",
            "blvd":"Boulevard",
            "blvd.": "Boulevard",
            "N":"North",
            "S":"South",
            "S.": "South",
            "Dr":"Drive",
            "Dr.":"Drive",
            "Pkwy":"Parkway",
            "apache":"Apache",
            "Ln.":"Lane"
                     }

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements
    # YOUR CODE HERE
    if element.tag == 'node':
        for node_field in node_attr_fields:
            node_attribs[node_field] = element.attrib[node_field]

        for child in element:
            if child.tag == 'tag':
                tag_temp = {}
                tag_temp = processtag_tags(element, child)
                if tag_temp != {}:
                    tags.append(tag_temp)


        return {'node': node_attribs, 'node_tags': tags}
    elif element.tag == 'way':
        for way_field in way_attr_fields:
            way_attribs[way_field] = element.attrib[way_field]

        position = 0
        for child in element:
            if child.tag == 'tag':
                tag_temp = {}
                tag_temp = processtag_tags(element, child)
                if tag_temp != {}:
                    tags.append(tag_temp)

            if child.tag == 'nd':
                way_nodes.append(processtag_nds(element, child, position))
                position += 1

        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}

def processtag_tags(element, child, problem_chars=PROBLEMCHARS, default_tag_type='regular'):

# 4 things to process here: key, type, id value. id first
    tag_temp = {}
    tag_temp['id'] = element.attrib['id']


    # if special char found
    if problem_chars.search(child.attrib['v']) != None\
        or is_ascii(child.attrib['v']) != True:
        return {}

# process key and type

    tag_temp['type'] = default_tag_type
    tag_temp['key'] = child.attrib['k']

    # no colon found
    if child.attrib['k'] == child.attrib['k'].split(':', 1)[0]:
        tag_temp['key'] = child.attrib['k']

    # if colon found
    elif child.attrib['k'] != child.attrib['k'].split(':', 1)[0]:
        tag_temp['key'] = child.attrib['k'].split(':', 1)[1]
        tag_temp['type'] = child.attrib['k'].split(':', 1)[0]

# process value
    tag_temp['value'] = correct_values(tag_temp['key'], child.attrib['v'])
    if tag_temp['value'] == -1:
        return {}

    return tag_temp

def processtag_nds(element, child, position):
    nd_temp = {}
    nd_temp['id'] = element.attrib['id']
    nd_temp['node_id'] = child.attrib['ref']
    nd_temp['position'] = position

    return nd_temp

def correct_values(tag_temp_key, tag_temp_value):
    # process street name
    if tag_temp_key == 'street':
        m = street_type_re.search(tag_temp_value)
        if m:
            street_type = m.group()
            if street_type in ROAD_NAME_MAPPING:
                tag_temp_value = tag_temp_value.replace(street_type, ROAD_NAME_MAPPING[street_type])

        """
        m = street_type_re.search(tag_temp_value)
        if m:
            street_type = m.group()
            if street_type not in ROAD_NAME_EXPECTED:
                pprint.pprint(street_type)
        """

        pass

    # process state name as abbr
    elif tag_temp_key == 'state':
        tag_temp_value = tag_temp_value.upper()
        if tag_temp_value not in STATES:
            if tag_temp_value == 'NEVADA':
                tag_temp_value = 'NV'
        pass

    # process postcode
    elif tag_temp_key == 'postcode':
        if tag_temp_value.split(' ')[0] != tag_temp_value:
            tag_temp_value = tag_temp_value.split(' ')[1]
        tag_temp_value = tag_temp_value.split('-')[0]

        if len(tag_temp_value) != 5 or tag_temp_value.isdigit() == False:
            return -1
        #pprint.pprint(tag_temp_value)

    return tag_temp_value

# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()
def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)

        raise Exception(message_string.format(field, error_string))
class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
                                                    k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in
                                                    row.iteritems()
                                                    })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
def is_ascii(s):
    return all(ord(c) < 128 for c in s)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """
    Iteratively process each XML element and write to csv(s)
"""
    with codecs.open(NODES_PATH, 'w') as nodes_file, \
            codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
            codecs.open(WAYS_PATH, 'w') as ways_file, \
            codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
            codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()


        validator = cerberus.Validator()
        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)

            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                    #pprint.pprint(el['node'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])
                    #pprint.pprint(el['way_tags'])


if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=False)