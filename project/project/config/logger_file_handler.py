

try:
    import codecs
except ImportError:
    codecs = None

import logging.handlers
import time
import os
from os import path
from datetime import datetime, timedelta

import logging.handlers as handlers

"""
    Handler for logging to a file, rotating the log file at certain timed
    intervals.
    
    If backupCount is > 0, when rollover is done, no more than backupCount
    files are kept - the oldest ones are deleted.
"""
class LoggerFileHandler(handlers.TimedRotatingFileHandler): # logging.handlers.TimedRotatingFileHandler
    is_locked = False  # Class Variable

    def __init__(self, filename, maxBytes=0, backupCount=0, encoding=None, delay=0, when='h', interval=1, utc=False):
        handlers.TimedRotatingFileHandler.__init__( self, filename, when, interval, backupCount, encoding, delay, utc)
        # self.maxBytes = maxBytes

    """
            do a rollover; in this case, a date/time stamp is appended to the filename
            when the rollover happens.  However, you want the file to be named for the
            start of the interval, not the current time.  If there is a backup count,
            then we have to get a list of matching filenames, sort them and remove
            the one with the oldest suffix.
    """
    def doRollover(self):
        file_name = self.baseFilename

        if self.stream:
            self.stream.close()
            self.stream = None
            try:
                if path.exists(file_name):
                    dirName, baseName = os.path.split(file_name)
                    #os.path.splitext(file_name)
                    baseName = baseName.rsplit('.', 1)[0]
                    new_file_name = dirName + "/" + baseName + "_" + datetime.strftime(datetime.now() - timedelta(1), '%Y-%m-%d') + ".log"
                    os.rename(file_name, new_file_name)
            except Exception as e:
                print(str(e))



                # get the time that this sequence started at and make it a TimeTuple
        currentTime = int(time.time())
        dstNow = time.localtime(currentTime)[-1]
        t = self.rolloverAt - self.interval
        if self.utc:
            timeTuple = time.gmtime(t)
        else:
            timeTuple = time.localtime(t)
            dstThen = timeTuple[-1]
            if dstNow != dstThen:
                if dstNow:
                    addend = 3600
                else:
                    addend = -3600
                timeTuple = time.localtime(t + addend)

        # dfn = self.rotation_filename(self.baseFilename + "." + time.strftime(self.suffix, timeTuple))
        dfn = self.rotation_filename(file_name)

        if os.path.exists(dfn):
            os.remove(dfn)
        self.rotate(self.baseFilename, dfn)
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)
        if not self.delay:
            self.stream = self._open()
        newRolloverAt = self.computeRollover(currentTime)
        while newRolloverAt <= currentTime:
            newRolloverAt = newRolloverAt + self.interval

        #If DST changes and midnight or weekly rollover, adjust for this.
        if (self.when == 'MIDNIGHT' or self.when.startswith('W')) and not self.utc:
            dstAtRollover = time.localtime(newRolloverAt)[-1]
            if dstNow != dstAtRollover:
                if not dstNow:  # DST kicks in before next rollover, so we need to deduct an hour
                    addend = -3600
                else:           # DST bows out before next rollover, so we need to add an hour
                    addend = 3600
                newRolloverAt += addend

        self.rolloverAt = newRolloverAt




# class LoggerFileHandler(logging.handlers.TimedRotatingFileHandler):
#     is_locked = False  # Class Variable
#
#     def __init__(self,dir_log):
#         self.dir_log = dir_log
#         filename =  self.dir_log + time.strftime("%m%d%Y")+".txt" #dir_log here MUST be with os.sep on the end
#         logging.handlers.TimedRotatingFileHandler.__init__(self, filename, when='midnight', interval=1, backupCount=0, encoding=None)
#
#     """
#         TimedRotatingFileHandler remix - rotates logs on daily basis, and filename of current logfile is time.strftime("%m%d%Y")+".txt" always
#     """
#     def doRollover(self):
#
#         is_waiting = False
#         while LoggerFileHandler.is_locked:
#             is_waiting=True
#             time.sleep(1) # making delay for 1 second
#         working_flag = True
#
#         self.stream.close()
#
#         # get the time that this sequence started at and make it a TimeTuple
#         t = self.rolloverAt - self.interval
#         timeTuple = time.localtime(t)
#
#         self.baseFilename = self.dir_log + time.strftime("%m%d%Y")+".txt"
#         if self.encoding:
#             self.stream = codecs.open(self.baseFilename, 'w', self.encoding)
#         else:
#             self.stream = open(self.baseFilename, 'w')
#
#         self.rolloverAt = self.rolloverAt + self.interval