import StringIO
import argparse
import datetime
import os
import os.path
import re
import sys
import urlparse
import xml.dom.minidom

import PyRSS2Gen

import helpers

parser = argparse.ArgumentParser(description = "Generate an RSS feed of a course.")
parser.add_argument("base", help="Base directory of Studio-dumped XML")
parser.add_argument("url_base", help="URL the feed will be hosted from")
parser.add_argument("--format", help="Format of RSS feed (mp4, webm, 3gp, or m4a)", default='webm', dest='format')
parser.add_argument("--course_url", help="URL of the course about page", default="https://www.edx.org/", dest="course_url")

args = parser.parse_args()

video_format = args.format
url_base = args.url_base
base = args.base

# Video format params
vfp = { 'mp4': {'vyd' : 'mp4', # Youtube downloader
                'vfn':'mp4', # Filename extension
                'vmt':'video/mp4', # MIME type
                'vdr': 'mp4',  # Directory
                'vcn': 'MPEG Video', # Video codec name
                'vdc': 'This RSS feed is for MPEG videos. This is the most common video format and should work with most software. ' # Description
                }, 
        'webm': {'vyd' : 'webm', # Youtube downloader
                'vfn':'webm', # Filename extension
                'vmt':'video/webm', # MIME type
                'vdr': 'webm',  # Directory
                'vcn': 'WebM Video', # Video codec name
                'vdc': 'This RSS feed is using WebM videos. WebM is an advanced video format developed by Goolgle. This is the recommended feed if your software supports it (most software does not). ' # Description
                }, 
        '3gp': {'vyd' : '3gp', # Youtube downloader
                'vfn':'3gp', # Filename extension
                'vmt':'video/3gpp', # MIME type
                'vdr': '3gp',  # Directory
                'vcn': '3GPP Video', # Video codec name
                'vdc': 'This RSS feed is for video files in the 3gpp format. 3gpp is a low-bandwidth format commonly used for video delivered to cell phones. ' # Description
                }, 
        'm4a': {'vyd' : '140', # Youtube downloader
                'vfn':'m4a', # Filename extension
                'vmt':'audio/mp4a-latm', # MIME type
                'vdr': 'm4a',  # Directory
                'vcn': 'AAC Audio', # Video codec name
                'vdc': 'This is an audio-only RSS feed. It uses the AAC audio codec. ' # Description
                }, 
        }

print base
tree = helpers.load_xml_course(base)

items = []

valid_youtube_id = re.compile("^[0-9a-zA-Z_\-]*$")

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
        
        base_filename = youtube_id+"."+vfp[video_format]['vfn']
        dl_filename = os.path.join('output', base_filename)
        if not os.path.exists(dl_filename):
            command = "youtube-dl -f {fmt} https://www.youtube.com/watch?v={uid} -o {file}".format(fmt=vfp[video_format]['vyd'], 
                                                                                                   uid=youtube_id, 
                                                                                                   file=dl_filename)
            os.system(command)
        item_dict['enclosure'] = PyRSS2Gen.Enclosure(url=urlparse.urljoin(url_base, base_filename),
                                                     length=os.stat(dl_filename).st_size,
                                                     type=vfp[video_format]['vmt'])
        items.append(PyRSS2Gen.RSSItem(**item_dict))

xml_org = tree.getroot().attrib['org']
xml_course = tree.getroot().attrib['course']
xml_url_name = tree.getroot().attrib['url_name']
xml_course_name = tree.getroot().attrib['display_name']

rss = PyRSS2Gen.RSS2(
    title = tree.getroot().attrib['display_name'],
    link = args.course_url,
    description = "A prototype podcast of the videos from {coursename}, a course from {org} on edX. The full course, including assessments, is available, free-of-charge, at {course_url}. {feedtype} Note that this is an interactive course; in some cases, the videos may be difficult to follow without the integrated interactive content on http://www.edx.org.".format(coursename=xml_course_name, org=xml_org, course_url = args.course_url, feedtype = vfp[video_format]['vdc']), 
    lastBuildDate = datetime.datetime.now(), 
    items = items, 
    managingEditor = "edX Learning Sciences"
    )

## Write output to a file
data = StringIO.StringIO()
rss.write_xml(data)
output_filename = "output/{org}_{course}_{url_name}_{format}.rss".format(org = xml_org, 
                                                                         course = xml_course, 
                                                                         url_name = xml_url_name, 
                                                                         format = video_format)
f = open(output_filename, "w")
f.write(xml.dom.minidom.parseString(data.getvalue()).toprettyxml())
f.close()
