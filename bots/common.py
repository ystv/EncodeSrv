import re


privmsg_re = re.compile(r"^<?@?([^ |^>]*)>?: *(.*)")