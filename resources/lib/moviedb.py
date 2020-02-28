#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import datetime

class Moviedb:
    def __init__(self):
        self.lastSyncTime = datetime.datetime.now()
        self.movies = []
        
    def isSyncNeed(self):
        thisTime = datetime.datetime.now()
        dTime = thisTime - self.lastSyncTime
        
        if dTime.seconds >= 180:
            return True

        if len(self.movies) == 0:
            return True
        
        return False
    
    def addMovie(self, movie):
        self.movies.append(movie)
