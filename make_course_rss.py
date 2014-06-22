import datetime
import os.path
import re
import sys
import StringIO
import xml.dom.minidom

import PyRSS2Gen

import helpers

video_format = "mp4"

# Video format params
vfp = { 'mp4': {'vyd' : 'mp4', # Youtube downloader
                'vfn':'mp4', # Filename extension
                'vmt':'video/mp4', # MIME type
                'vdr': 'mp4',  # Directory
                'vcn': 'MPEG Video' # Video codec name
                }
        }

print sys.argv[1]
tree = helpers.load_xml_course(sys.argv[1])

items = []

valid_youtube_id = re.compile("^[0-9a-zA-Z_]*$")

## Add videos
for e in tree.iter():
    item_dict = dict()
    if e.tag in ['video']: 
        if 'youtube_id_1_0' not in e.attrib:
            continue
        item_dict['title'] = e.attrib['display_name']
        item_dict['guid'] = e.attrib['url_name']
        youtube_id = e.attrib['youtube_id_1_0']
        if not valid_youtube_id.match(youtube_id):
            raise TypeError("Youtube ID has an invalid string. Security issue?")
        item_dict['link'] = "https://www.youtube.com/watch?v="+youtube_id
        description = list()
        node = e
        while node != None:
            if 'display_name' in node.attrib:
                description.append(node.attrib['display_name'])
            node = node.parent
        description.reverse()
        
        item_dict['description'] = "edX RSS Prototype. Video is from "+(" / ".join(description))
        
        dl_filename = os.path.join('output', youtube_id+"."+vfp[video_format]['vfn'])
        if not os.path.exists(dl_filename):
            command = "youtube-dl -f {fmt} https://www.youtube.com/watch?v={uid} -o {file}".format(fmt=vfp[video_format]['vyd'], 
                                                                                                   uid=youtube_id, 
                                                                                                   file=dl_filename)
            os.system(command)
        #video_url = "http://foo.com"
        #item_dict['enclosure'] = video_url
        #print e.attrib['youtube_id_1_0']
        #print 
        items.append(PyRSS2Gen.RSSItem(**item_dict))

rss = PyRSS2Gen.RSS2(
    title = "edX Course", 
    link = "http://www.edx.org",
    description = "A prototype podcast of the videos from {coursename}, a course from {org} on edX. The full course, including assessments, is available, free-of-charge, at http://www.edx.org/".format(coursename=tree.getroot().attrib['display_name'], org=tree.getroot().attrib['org']), 
    lastBuildDate = datetime.datetime.now(), 
    items = items, 
    managingEditor = "edX Learning Sciences"
    )

## Write output to a file
data = StringIO.StringIO()
rss.write_xml(data)
f = open("output/course.rss", "w")
f.write(xml.dom.minidom.parseString(data.getvalue()).toprettyxml())
f.close()
