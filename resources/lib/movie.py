#!/usr/bin/env python
# -*- coding: utf-8 -*- 

class Movie:
    def __init__(self, name, url, genre, year, title, thumbnailurl, projectstatus):
        self.name = name
        self.url = url
        self.genre = genre
        self.year = year
        self.title = title
        self.thumbnailurl = thumbnailurl
        self.projectstatus = projectstatus
        self.categories = []
        
    def inCategory(self, category):
        if category in self.categories:
            return True
        
        return False
    
    def addCategory(self, category):
        self.categories.append(category)