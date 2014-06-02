# Basedn on a one-off script by Chris Terman
#
# (Slightly) productionized by Piotr Mitros. Mistakes belong to Piotr
# Mitros. Credit belongs to cjt.

import argparse
import json
import os,os.path
import re
import sys

import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description = "Clean up XML spat out by Studio.")
parser.add_argument("base", help="Base directory of Studio-dumped XML")
parser.add_argument("output", help="Location of cleaned output file")
args = parser.parse_args()

# given element of the form <foo url_name="...">, if there's a directory named "tag",
# parse the file named by the "url_name" attribute and add subtree as a child of element.
# Recursively load each subtree, add parent pointers so we can walk up the tree.
def load_subtree(element):
    if os.path.isdir(os.path.join(args.base, element.tag)) and element.attrib.has_key('url_name'):
        subtree = ET.parse(os.path.join(args.base, element.tag,element.attrib['url_name']+'.xml')).getroot()
        for child in subtree:
            load_subtree(child)
        if subtree.tag == element.tag:
            # some elements are place holders with a "url_name" attribute
            # pointing to another file with a top-level element with the
            # same tag.  Eg
            #  <video url_name="foo">
            # refers to a file video/foo.xml that has the actual
            # <video> tag with all the relevant info

            # this code merges those two levels of the tree
            element.text = subtree.text
            element.tail = subtree.tail
            for a,v in subtree.items():
                element.set(a,v)
            for child in subtree:
                element.append(child)
                child.parent = element
        else:
            element.append(subtree)
            subtree.parent = element

# starting with element, move up the DOM tree looking for tag
def find_parent(element,tag):
    while True:
        if element is None or element.tag == tag:
            return element
        element = element.parent

# get root of course XML tree
tree = ET.parse(os.path.join(args.base, 'course.xml'))
root = tree.getroot()
root.parent = None

# load the XML for the entire course
load_subtree(root)

output = ET.tostring(root) # TODO: Tounicode

output_file = open(args.output, "w")
output_file.write(output)
output_file.close()
