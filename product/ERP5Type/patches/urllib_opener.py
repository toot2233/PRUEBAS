# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2007 Nexedi SARL and Contributors. All Rights Reserved.
#                    Jean-Paul Smets <jp@nexedi.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

# Install openers
# -> testTemplateTool.TestTemplateTool.test_getBusinessTemplateUrl
import urllib.request, urllib.parse, urllib.error
from io import BytesIO
import socket
import os
import mimetypes
import six
if six.PY2:
    from email import message_from_file as message_from_bytes
else:
    from email import message_from_bytes
from email.utils import formatdate

class DirectoryFileHandler(urllib.request.FileHandler):
    """
    Extends the file handler to provide an HTML
    representation of local directories.
    """

    # Use local file or FTP depending on form of URL
    def file_open(self, req):
        if six.PY2:
            url = req.get_selector()
        else:
            url = req.selector
        if url[:2] == '//' and url[2:3] != '/':
            req.type = 'ftp'
            return self.parent.open(req)
        else:
            return self.open_local_file(req)

    # not entirely sure what the rules are here
    def open_local_file(self, req):
        if six.PY2:
            host = req.get_host()
            file = req.get_selector()
        else:
            host = req.host
            file = req.selector
        localfile = urllib2.url2pathname(file)
        stats = os.stat(localfile)
        size = stats.st_size
        modified = formatdate(stats.st_mtime, usegmt=True)
        mtype = mimetypes.guess_type(file)[0]
        headers = message_from_bytes(BytesIO(
            'Content-type: %s\nContent-length: %d\nLast-modified: %s\n' %
            (mtype or 'text/plain', size, modified)))
        if host:
            host, port = urllib.parse.splitport(host)
        if not host or \
           (not port and socket.gethostbyname(host) in self.get_names()):
            try:
              file_list = os.listdir(localfile)
              s = BytesIO()
              s.write('<html><head><base href="%s"/></head><body>' % ('file:' + file))
              s.write('<p>Directory Content:</p>')
              for f in file_list:
                s.write('<p><a href="%s">%s</a></p>\n' % (urllib.parse.quote(f), f))
              s.write('</body></html>')
              s.seek(0)
              headers = message_from_bytes(BytesIO(
                  'Content-type: %s\nContent-length: %d\nLast-modified: %s\n' %
                  ('text/html', size, modified)))
              return urllib2.addinfourl(s, headers, 'file:' + file)
            except OSError:
              return urllib2.addinfourl(open(localfile, 'rb'),
                                        headers, 'file:'+file)
        raise urllib.error.URLError('file not on local host')
opener = urllib.request.build_opener(DirectoryFileHandler)
urllib.request.install_opener(opener)
