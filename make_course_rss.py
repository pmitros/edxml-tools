import datetime
import PyRSS2Gen

items = []

rss = PyRSS2Gen.RSS2(
    title = "edX Course", 
    link = "http://www.edx.org",
    description = "Videos from an edX course. The full course is available, free-of-charge, at http://www.edx.org/", 
    lastBuildDate = datetime.datetime.now(), 
    items = items
    )

f = open("course.rss", "w")
rss.write_xml(open("course.rss", "w"))
f.close()
