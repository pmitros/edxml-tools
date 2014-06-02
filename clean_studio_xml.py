# Basedn on a one-off script by Chris Terman
#
# (Slightly) productionized by Piotr Mitros. Mistakes belong to Piotr
# Mitros. Credit belongs to cjt.

import argparse
import json
import os,os.path
import re
import sys

import xml.etree
import xml.etree.ElementTree as ET


parser = argparse.ArgumentParser(description = "Clean up XML spat out by Studio.")
parser.add_argument("base", help="Base directory of Studio-dumped XML")
args = parser.parse_args()


shre = re.compile("^[a-f0-9]+$")
def studio_hash(s):
    ''' Check if a string is a Studio-generated hash '''
    if len(s) == len("d750387a715f4c0e981efebe128ff754") and shre.match(s):
        return True
    return False

def url_slug(s):
    ''' Return a string appropriate for embedding in a URL. 
    For example, "Hello, Mr. Rogers!" will convert to "Hello_Mr._Rogers"
    '''

    # Step 1: Replace non-alphanumeric characters with underscores
    new_string = str()
    for i in range(len(s)):
        if s[i].isalnum():
            new_string = new_string + s[i]
        else:
            new_string = new_string + '_'

    # Step 2: Remove underscores at the end
    while new_string[-1] == '_':
        new_string = new_string[:-1]
    if len(new_string) == 0:
        new_string = "_"

    # Step 3: Consolidate repeated underscores
    new_string = new_string.replace("_____", "_")
    new_string = new_string.replace("___", "_")
    new_string = new_string.replace("__", "_")

    return new_string

used_url_names = set()
def unique_url_slug(s):
    ''' Check if we've seen 's' before, and if so, '''
    new_string = url_slug(s)
    if new_string in used_url_names:
        i = 0
        while new_string+"_"+str(i) in used_url_names:
            i = i+1
            continue
        new_string = new_string+"_"+str(i)
    used_url_names.add(new_string)
    return new_string

display_map = {}
def set_url_name_slug(e, new_name):
    ''' Maintain a mapping from new URL names to old ones for e.g. analytics. 
    We'll keep the mapping in static files. 
    '''
    new_name = unique_url_slug(new_name)
    display_map[new_name] = e.attrib['url_name']
    e.attrib['url_name'] = new_name

def load_subtree(element):
    ''' given element of the form <foo url_name="...">, if there's a directory named "tag",
    parse the file named by the "url_name" attribute and add subtree as a child of element.
    Recursively load each subtree, add parent pointers so we can walk up the tree. '''
    if 'url_name' not in element.attrib:
        return

    filename = os.path.join(args.base, element.tag,element.attrib['url_name']+'.xml')

    if os.path.isdir(os.path.join(args.base, element.tag)) and element.attrib.has_key('url_name'):
        if not os.path.exists(filename):
            for child in element: 
                child.parent = element
                load_subtree(child)
            return
        subtree = ET.parse(os.path.join(args.base, element.tag,element.attrib['url_name']+'.xml')).getroot()
        os.unlink(filename)
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

# get root of course XML tree and load the XML for the entire course
tree = ET.parse(os.path.join(args.base, 'course.xml'))
root = tree.getroot()
root.parent = None
load_subtree(root)

## Now, we'll clean up the URL names Studio assigned
# Step 1: Fill up the namespace with existing URL slugs. These must be unique. 
for e in tree.iter():
    if 'url_name' in e.attrib:
        unique_url_slug(e.attrib['url_name'])

# Step 2: If we have a Studio-assigned URL name, but we do have a display name,
# change the URL name to be a sluggification of the display name
for e in tree.iter():
    if 'display_name' in e.attrib and studio_hash(e.attrib['url_name']):
        set_url_name_slug(e, e.attrib['display_name'])

## Step 3: We'll clean up the filenames Studio assigned for our HTML files
for e in tree.iter():
    if 'filename' in e.attrib and os.path.exists(os.path.join(args.base, 'html', e.attrib['filename'])+".html") and studio_hash(e.attrib['filename']):
        oldpath = os.path.join(args.base, 'html', e.attrib['filename'])+".html"
        if 'url_name' in e.attrib:
            slug = e.attrib['url_name']
        newpath = os.path.join(args.base, 'html', slug)+".html"
        if not os.path.exists(newpath):
            os.rename(oldpath, newpath)
            e.attrib['filename'] = slug

## Step 4: We'll add discussion tags where relevant
## 
## If we don't have a nice name, we'll assume the discussion is 
## about the previous node in the tree. 
for e in tree.iter():
    if e.tag == 'discussion': 
        related_index = e.parent._children.index(e)-1
        if related_index >= 0: 
            related_node = e.parent._children[related_index]
            if studio_hash(e.attrib['url_name']):
                set_url_name_slug(e, related_node.attrib['url_name'] + '_discussion')
            if not 'discussion_target' in e.attrib or studio_hash(e.attrib['discussion_target']):
                if 'display_name' in related_node.attrib:
                    e.attrib['discussion_target'] = related_node.attrib['display_name']


# We're done. Dump course.xml back to the file system
output = ET.tostring(root) # TODO: Tounicode
output_file = open(os.path.join(args.base, 'course.xml'), "w")
output_file.write(output)
output_file.close()

# And finally, dump the mapping file
mapping_filename = os.path.join(args.base, 'static/urlname_mapping.json')
i = 0
while os.path.exists(mapping_filename):
    mapping_filename = os.path.join(args.base, 'static/urlname_mapping_{i}.json'.format(i=i))
    i = i+1

mapping_file = open(mapping_filename, "w")
mapping_file.write(json.dumps(display_map, indent=2))
mapping_file.close()
