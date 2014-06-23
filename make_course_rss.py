''' This is a script which will take an edX course export, and create
an RSS feed from it.

I *strongly* recommend running clean_studio_xml on a dump before
running this script.

Limitations: 

* This does not pay attention to release dates. To-be-released videos
  can appear in the RSS feed.
* Courses must use Youtube videos. I use Youtube as a
  transcoder. Google invested millions into doing this well, and I
  didn't want to replicate the effort. As a result, if Google changes
  things around, we may need to swap things around.
* We don't have course URLs by default. This sure would be nice. 
* It would be nice to embed pages for where we have assessments and
  interactives. RSS supports this, but the script does not (in part
  due to complexity of generating URLs). 

If you'd like to do this a lot, generate a Google API key, and use the
environment variables: GOOGLE_DEVID and GOOGLE_DEVKEY. Google locks
you out pretty quickly without those. 
'''

import StringIO
import argparse
import datetime
import json
import os
import os.path
import re
import sys
import urlparse
import xml.dom.minidom

import PyRSS2Gen

import helpers

parser = argparse.ArgumentParser(description = "Generate an RSS feed of a course.")
parser.add_argument("export_base", help="Base directory of Studio-dumped XML")
parser.add_argument("url_base", help="URL the feed will be hosted from")
parser.add_argument("--format", help="Format of RSS feed (mp4, webm, 3gp, or m4a)", default='webm', dest='format')
parser.add_argument("--course_url", help="URL of the course about page", default="https://www.edx.org/", dest="course_url")

args = parser.parse_args()


# Video format params
video_format_parameters = { 'mp4': {'youtube_dl_code' : 'mp4', 
                                    'video_extension':'mp4', 
                                    'mimetype':'video/mp4', 
                                    'video_codec_name': 'MPEG Video', 
                                    'codec_description': 'This RSS feed is for MPEG videos. This is the most common video format and should work with most software. ' 
                                    }, 
                            'webm': {'youtube_dl_code' : 'webm', 
                                     'video_extension':'webm', 
                                     'mimetype':'video/webm', 
                                     'video_codec_name': 'WebM Video', 
                                     'codec_description': 'This RSS feed is using WebM videos. WebM is an advanced video format developed by Google. This is the recommended feed if your software supports it (most software does not). ' 
                                     }, 
                            '3gp': {'youtube_dl_code' : '3gp', 
                                    'video_extension':'3gp', 
                                    'mimetype':'video/3gpp', 
                                    'video_codec_name': '3GPP Video', 
                                    'codec_description': 'This RSS feed is for video files in the 3gpp format. 3gpp is a low-bandwidth format commonly used for video delivered to cell phones. ' 
                                    }, 
                            'm4a': {'youtube_dl_code' : '140', 
                                    'video_extension':'m4a', 
                                    'mimetype':'audio/mp4a-latm', 
                                    'video_codec_name': 'AAC Audio', 
                                    'codec_description': 'This is an audio-only RSS feed. It uses the AAC audio codec. ' 
                                    }, 
                            }

video_format = args.format
conf = { 'video_format' : args.format, 
         'url_base' : args.url_base, 
         'export_base' : args.export_base, 
         'course_url':args.course_url,
         'mimetype' : video_format_parameters[video_format]['mimetype'], 
         'codec_description' : video_format_parameters[video_format]['codec_description'], 
         'video_codec_name' : video_format_parameters[video_format]['video_codec_name'], 
         'youtube_dl_code' : video_format_parameters[video_format]['youtube_dl_code'], 
         'video_extension' : video_format_parameters[video_format]['video_extension'], 
         'podcast_title' : "Videos from {course_org} : {course_name} on edX", 
         'podcast_description': '''A prototype podcast of the videos from {course_name}, a course from {course_org} on edX. The full course, including assessments, is available, free-of-charge, at {course_url}. {codec_description} Note that this is a podcast of just the videos from an interactive on-line course; in some cases, the videos may be difficult to follow without integrated assessments, simulations, or other interactions at {course_url}. RSS feeds for other codecs are available. For a more complete experience, please visit the full course. ''',
         'video_description': '''{youtube_description} {video_location}. This is a prototype podcast of the videos from {course_name}. The full course is available free-of-charge at {course_url}. Note that the full course includes assessments, as well as other interactives (such as simulations, discussions, etc.). Some videos may be difficult to follow without the integrated interactions. For a more complete experience, please visit the full course. ({pretty_length}, {duration}, {video_codec_name}) ''',
         }

print "Encoding", conf['export_base']
tree = helpers.load_xml_course(conf['export_base'])

conf.update({'course_org' : tree.getroot().attrib['org'],
             'course_number' : tree.getroot().attrib['course'],
             'course_id' : tree.getroot().attrib['url_name'],
             'course_name' : tree.getroot().attrib['display_name']})

items = []

valid_youtube_id = re.compile("^[0-9a-zA-Z_\-]*$")

## Add videos
for e in tree.iter():
    item_dict = dict()
    if e.tag in ['video']: 
        if 'youtube_id_1_0' not in e.attrib:
            continue
        youtube_id = e.attrib['youtube_id_1_0']
        youtube_cache = os.path.join('output', youtube_id + ".json")
        if not os.path.exists(youtube_cache):
            youtube_info = helpers.youtube_entry(youtube_id)
            f = open(youtube_cache, "w")
            json.dump(youtube_info, f)
            f.close()
        else:
            youtube_info = json.load(open(youtube_cache))
        item_dict['title'] = e.attrib['display_name']
        if item_dict['title'] == 'Video':
            item_dict['title'] = youtube_info['title']
        item_dict['guid'] = e.attrib['url_name']
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
        
        
        base_filename = youtube_id+"."+conf['video_extension']
        dl_filename = os.path.join('output', base_filename)
        if not os.path.exists(dl_filename):
            command = "youtube-dl -f {fmt} https://www.youtube.com/watch?v={uid} -o {file}".format(fmt=conf['youtube_dl_code'], 
                                                                                                   uid=youtube_id, 
                                                                                                   file=dl_filename)
            os.system(command)
        length = os.stat(dl_filename).st_size
        pretty_length = helpers.format_file_size(length)

        youtube_description = youtube_info['description']
        if not youtube_description:
            youtube_description = ""
        if len(youtube_description) > 0 and youtube_description[-1]!=' ':
            youtube_description = youtube_description + ' '

        item_dict['description'] = conf['video_description'].format(youtube_description = youtube_description,
                                                                    video_location = (" / ".join(description)), 
                                                                    pretty_length = pretty_length, 
                                                                    duration = youtube_info['duration_str'], 
                                                                    **conf)

        item_dict['enclosure'] = PyRSS2Gen.Enclosure(url=urlparse.urljoin(conf['url_base'], base_filename),
                                                     length=length,
                                                     type=conf['mimetype'])
        items.append(PyRSS2Gen.RSSItem(**item_dict))

items.reverse()

rss = PyRSS2Gen.RSS2(
    title = conf["podcast_title"].format(**conf), 
    link = args.course_url,
    description = conf["podcast_description"].format(**conf), 
    lastBuildDate = datetime.datetime.now(), 
    items = items, 
    managingEditor = "edX Learning Sciences"
    )

## Write output to a file
data = StringIO.StringIO()
rss.write_xml(data)
output_filename = "output/{org}_{course}_{url_name}_{format}.rss".format(org = conf['course_org'], 
                                                                         course = conf['course_number'], 
                                                                         url_name = conf['course_id'], 
                                                                         format = video_format)
f = open(output_filename, "w")
f.write(xml.dom.minidom.parseString(data.getvalue()).toprettyxml())
f.close()
print "Saved ", output_filename
