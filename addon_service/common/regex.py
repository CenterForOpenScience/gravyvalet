import re


uri_regex = re.compile(r"http://[^/]+/(?P<id>\w{5})/?")
