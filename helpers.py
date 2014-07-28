import datetime
import json
import os,os.path
import re
import sys

import xml.etree
import xml.etree.ElementTree as ET

import xml.dom.minidom

shre = re.compile("^[a-f0-9]+$")
def studio_hash(s):
    ''' Check if a string is a Studio-generated hash '''
    if len(s) == len("d750387a715f4c0e981efebe128ff754") and shre.match(s):
        return True
    return False

def url_slug(unsluggified, unique=True):
    ''' Return a sluggified string appropriate for embedding in a URL. 
    For example, "Hello, Mr. Rogers!" will convert to "Hello_Mr._Rogers"
    The string is guaranteed to have only letters, numbers, and underscores. 

    It is not guaranteed to be unique. 
    '''
    if unique: 
        return _make_unique_url_slug(unsluggified)
    else: 
        return _url_slug_encode(unsluggified)

def save_url_name_slugs(tree):
    ''' Go through the tree. Save all of the url_names, so when we do
    unique slug encodes, we don't reuse them. 
    '''
    for e in tree.iter():
        if 'url_name' in e.attrib:
            _make_unique_url_slug(e.attrib['url_name'])

def propagate_display_to_url_name(tree):
    ''' If we have a Studio-assigned URL name, but we do have a display name,
    change the URL name to be a sluggification of the display name '''
    for e in tree.iter():
        if 'display_name' in e.attrib and studio_hash(e.attrib['url_name']):
            set_url_name_slug(e, e.attrib['display_name'])

display_map = {}
def set_url_name_slug(e, new_name):
    ''' Maintain a mapping from new URL names to old ones for e.g. analytics. 
    We'll keep the mapping in static files. 
    '''
    new_name = url_slug(new_name, unique=True)
    display_map[new_name] = e.attrib['url_name']
    e.attrib['url_name'] = new_name

def save_url_name_map(basepath):
    ''' Save a mapping from old url names to new url names.
    This way, we can resconstruct between processed/unprocessed courses between 
    runs. '''

    mapping_filename = os.path.join(basepath, 'static/urlname_mapping.json')
    i = 0
    while os.path.exists(mapping_filename):
        mapping_filename = os.path.join(basepath, 'static/urlname_mapping_{i}.json'.format(i=i))
        i = i+1

    mapping_file = open(mapping_filename, "w")
    mapping_file.write(json.dumps(display_map, indent=2))
    mapping_file.close()

def propagate_urlname_to_filename(tree, basepath):
    ''' Rename horrific Studio names for files to be the same as nice new url_names''' 
    for e in tree.iter():
        if 'filename' in e.attrib and  \
                os.path.exists(os.path.join(basepath, 'html', e.attrib['filename'])+".html") and \
                studio_hash(e.attrib['filename']):
            oldpath = os.path.join(basepath, 'html', e.attrib['filename'])+".html"
            if 'url_name' in e.attrib:
                slug = e.attrib['url_name']
            newpath = os.path.join(basepath, 'html', slug)+".html"
            if not os.path.exists(newpath):
                os.rename(oldpath, newpath)
                e.attrib['filename'] = slug

def left_sibling_node(node):
    ''' Find the node directly above a given node. 
    '''
    related_index = node.parent._children.index(node)-1
    if related_index >= 0: 
        related_node = node.parent._children[related_index]
        return related_node
    return None

def propagate_sibling_tags(tree):
    ''' If a discussion node has an automatic name, assume it is about
    the node above it, and use that as a URL name with _discussion at the end. 

    Use display names for discussion targets. 
    '''
    for e in tree.iter():
        if e.tag in ['discussion']: 
            related_node = left_sibling_node(e)
            if related_node == None:
                continue
            if studio_hash(e.attrib['url_name']) and not studio_hash(related_node.attrib['url_name']):
                set_url_name_slug(e, related_node.attrib['url_name'] + '_' + e.tag)
            if not 'discussion_target' in e.attrib or studio_hash(e.attrib['discussion_target']):
                if 'display_name' in related_node.attrib and not studio_hash(related_node.attrib['display_name']):
                    e.attrib['discussion_target'] = related_node.attrib['display_name']

def _url_slug_encode(s):
    ''' Return a sluggified string appropriate for embedding in a URL. 
    For example, "Hello, Mr. Rogers!" will convert to "Hello_Mr._Rogers"
    The string is guaranteed to have only letters, numbers, and underscores. 

    It is not guaranteed to be unique. 
    '''

    # Step 1: Replace non-alphanumeric characters with underscores
    new_string = str()
    for i in range(len(s)):
        if s[i].isalnum():
            new_string = new_string + s[i]
        else:
            new_string = new_string + '_'

    # Step 2: Remove underscores at the end
    
    while len(new_string)>0 and new_string[-1] == '_':
        new_string = new_string[:-1]
    if len(new_string) == 0:
        new_string = "_"

    # Step 3: Consolidate repeated underscores
    new_string = new_string.replace("_____", "_")
    new_string = new_string.replace("___", "_")
    new_string = new_string.replace("__", "_")

    return new_string

used_url_names = set()
def _make_unique_url_slug(s):
    ''' 
    Return a sluggified string appropriate for embedding in a URL. 
    For example, "Hello, Mr. Rogers!" will convert to "Hello_Mr._Rogers"
    The string is guaranteed to have only letters, numbers, and underscores. 

    It is guaranteed to be unique. If the slug occured before, an
    incrementing suffix is added.
    '''
    new_string = _url_slug_encode(s)
    if new_string in used_url_names:
        i = 0
        while new_string+"_"+str(i) in used_url_names:
            i = i+1
            continue
        new_string = new_string+"_"+str(i)
    used_url_names.add(new_string)
    return new_string

def load_xml_course(directory_base):
    ''' Load a course from edXML, and return an xml.etree object
    '''
    tree = ET.parse(os.path.join(directory_base, 'course.xml'))
    root = tree.getroot()
    root.parent = None
    load_subtree(directory_base, root)
    return tree

def load_subtree(directory_base, element):
    ''' given element of the form <foo url_name="...">, if there's a directory named "tag",
    parse the file named by the "url_name" attribute and add subtree as a child of element.
    Recursively load each subtree, add parent pointers so we can walk up the tree.

    This function is based on a one-off script by Chris Terman
    (Slightly) productionized by Piotr Mitros. Mistakes belong to Piotr
    Mitros. Credit belongs to cjt. '''

    if 'url_name' not in element.attrib:
        return

    filename = os.path.join(directory_base, element.tag,element.attrib['url_name']+'.xml')

    if os.path.isdir(os.path.join(directory_base, element.tag)) and element.attrib.has_key('url_name'):
        if not os.path.exists(filename.encode('utf-8')):
            for child in element: 
                child.parent = element
                load_subtree(directory_base,child)
            return
        subtree = ET.parse(os.path.join(directory_base, element.tag,element.attrib['url_name']+'.xml')).getroot()
        os.unlink(filename)
        for child in subtree:
            load_subtree(directory_base,child)
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

def save_tree(basepath, tree):
    for e in tree.findall(".//problem"):
        if 'url_name' not in e.attrib:
            continue
        problemfile = open(os.path.join(basepath, 'problem/{problem}.xml'.format(problem=e.attrib["url_name"])), "w")
        problemfile.write(ET.tostring(e))
        problemfile.close()
        del e._children[:]
        e.text = ''
        for key in list(e.attrib):
            if key != 'url_name':
                del e.attrib[key]

    output = ET.tostring(tree.getroot()) # TODO: Tounicode
    output_file = open(os.path.join(basepath, 'course.xml'), "wb")
    md = xml.dom.minidom.parseString(output)
    pxml = md.toprettyxml(indent='  ')
    output_file.write(pxml.encode('utf-8'))
    output_file.close()

yt_service = None
def youtube_entry(video):
    global yt_service
    if not yt_service:
        import gdata.youtube.service
        yt_service = gdata.youtube.service.YouTubeService()
        if 'GOOGLE_DEVKEY' in os.environ:
            yt_service.ssl = True
            yt_service.developer_key = os.environ['GOOGLE_DEVKEY']
        if 'GOOGLE_DEVID' in os.environ:
            yt_service.client_id = os.environ['GOOGLE_DEVID']

    # TODO: Parse traditional XML entries. 
    # Handle both XML <video> elements and straight-up Youtube IDs
    if not isinstance(video, basestring):
        video_id = video.attrib.get('youtube_id_1_0', None)
    else: 
        video_id = video
    if not video_id:
        return

    entry = yt_service.GetYouTubeVideoEntry(video_id=video_id)
    return {'title': entry.media.title.text, 
            'duration': float(entry.media.duration.seconds), 
            'duration_str': format_time_delta(entry.media.duration.seconds),
            'description' : entry.media.description.text}

def format_time_delta(time):
    ''' Pretty-print a time delta. Parameters is number of seconds. '''
    time_delta = str(datetime.timedelta(seconds = int(time)))
    # Strip trailing 00:0 from 00:03:45
    while time_delta[:1] in "0:":
        time_delta = time_delta[1:]
    # If time delta is 0, continue
    if len(time_delta) == 0:
        time_delta = "0"
    return time_delta

def propagate_youtube_information(tree):
    ''' Retrieve information from Youtube. Use it to set 
    display_names for videos. 

    This is untested. 
    '''
    for e in tree.iter():
        if e.tag in ['video']: 
            # Skip videos for which we have names already
            if not studio_hash(e.attrib['display_name']) and \
                    e.attrib['display_name'].lower() != 'Video':
                continue
            # If we're not streaming from Youtube, skip it
            vid_info = youtube_entry(e)
            if not vid_info: 
                continue
            e.attrib['display_name'] = "{title} ({duration})".format(title=vid_info['title'], 
                                                           duration=vid_info['duration_str'])

def format_file_size(num):
    ''' Format a number of bytes into a human-readable size. 
    http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
    '''
    for x in ['bytes','KB','MB','GB']:
        if num < 1024.0 and num > -1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')

def clean_json(base, filename):
    ''' If filename exists, load it, and save it, with JSON pretty-printed '''
    fn = os.path.join(base, filename)
    if os.path.exists(fn):
        j = json.load(open(fn))
        fp = open(fn, "w")
        json.dump(j, fp, indent=2, sort_keys=True)
        fp.close()
