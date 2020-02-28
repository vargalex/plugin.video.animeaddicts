#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import requests
from HTMLParser import HTMLParser

session = requests.Session()
page = session.get('http://animeaddicts.hu/project.php?completed.jap').text

class MyHTMLParser(HTMLParser):
  def __init__(self):
    HTMLParser.__init__(self)
    self.recording = 0 
    self.data = []
    
  def handle_starttag(self, tag, attrs):
    if tag == 'div':
      for name, value in attrs:
        if name == 'class' and value == 'box':
          print name, value
          print "Encountered the beginning of a %s tag" % tag 
          self.recording = 1 

  def handle_endtag(self, tag):
    if tag == 'div' and self.recording:
      self.recording -=1 
      print "Encountered the end of a %s tag" % tag 

  def handle_data(self, data):
    if self.recording:
      self.data.append(data)

p = MyHTMLParser()
p.feed(page)
print p.data
p.close()