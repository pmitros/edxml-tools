edxml-tools
===========

This repository has some tools for manipulating edXML. Specifically,
at this point, it has one tool: clean_studio_xml.py. 

This tool started with a chunk of code from Chris Terman which took
the Studio-exported XML and put it all in one big file. It was
something a human could edit without pulling teeth quite as
much. Neat!

I took this, and modified it to, as much as possible, strip out
Studio-generated IDs and replace them with human-readable slugs. If
you export a course, run this tool over it, and import it back in,
you'll notice a few changes:

1. Unit identifiers in Studio will mostly be human-readable. instead
of something like 'cdba7b0a6ea548bc9df43b17c560b6cc', you'll see
something like 'Create_a_few_problems'.
2. As a corollary, Analytics, data exports, gradebooks, etc. will
become much more human-friendly.
3. Forums will have discussion targets set. 

Note that you should never do this to a running course. Changing the
IDs will, in fact, cause the system to forget all the work your
students did. However, doing this before a course rerun will make your
life much easier.

This code is not bombproof. 

1. You should check and double-check the output before this hits
students.
2. Studio is a bit broken in how it handles drafts/public versions in
imports/exports. Studio has a horrible hack, which this code does not
support. Make everything public before exporting.

This code does save a mapping between your old URL names and new ones
in the static directory. This will make it possible to compare
analytics and similar between runs.