import argparse

import helpers

parser = argparse.ArgumentParser(description = "Clean up XML spat out by Studio.")
parser.add_argument("base", help="Base directory of Studio-dumped XML")
args = parser.parse_args()

## Helper functions ##

# get root of course XML tree and load the XML for the entire course
tree = helpers.load_xml_course(args.base)

# Save the slugs used in the course, so we don't run into collisions while renaming
helpers.save_url_name_slugs(tree)

# Untested: Extract names from Youtube video titles, etc. 
# helpers.propagate_youtube_information(tree)

## Propagate names down from parents to children
helpers.propagate_display_between_parent_and_child(tree)

# Give URL names based on display names
helpers.propagate_display_to_url_name(tree)

## We'll clean up the filenames Studio assigned for our HTML files
helpers.propagate_urlname_to_filename(tree, args.base)

## Add discussion tags where relevant. Add display names to discussions. 
## 
## If we don't have a nice name, we'll assume the discussion is 
## about the previous node in the tree. 
helpers.propagate_sibling_tags(tree)

# We're done. Dump problems and course.xml back to the file system
helpers.save_tree(args.base, tree)

# And finally, dump the mapping file
#
# TODO: Merge line below
# 
# if not os.path.exists(os.path.join(args.base, 'static')):
#    os.mkdir(os.path.join(args.base, 'static'))

helpers.save_url_name_map(args.base)

# Now, we clean up a few JSON files. 
for filename in ['policies/edx/policy.json', 'policies/edx/grading_policy.json']:
    helpers.clean_json(args.base, filename)
        
