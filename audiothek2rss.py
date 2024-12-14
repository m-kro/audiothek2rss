# Copyright (c) 2024, Mirko Barthauer
# All rights reserved.

# This source code is licensed under the MIT-style license found in the
# LICENSE file in the same directory of this source tree.

import os, sys
import requests
import argparse
import html
import unicodedata
import shutil
from datetime import datetime
import xml.etree.ElementTree as ET
from time import sleep

class AudiothekCategory(object):
    
    def __init__(self, id, title):
        self.id = id
        self.title = title
        self.programSets = []
        
    def addProgramSet(self, programSet):
        self.programSets.append(programSet)
        
    def addProgramSets(self, programSets):
        self.programSets.extend(programSets)
        
class AudiothekProgramSet(object):
    
    def __init__(self, id, title, sharingUrl="", description="", synopsis="", imageUrl=""):
        self.id = id
        self.title = title
        self.sharingUrl = sharingUrl
        self.description = description
        self.synopsis = synopsis
        self.rssPath = None
        self.audiothekPath = None
        self.imageUrl = imageUrl if len(imageUrl) > 0 else None
        self.items = []
    
    def hasItems(self):
        return len(self.items) > 0
    
    def addItem(self, item):
        self.items.append(item)
        item.programSet = self
        
    def addItems(self, addItems):
        self.items.extend(addItems)
        for item in addItems:
            item.programSet = self
    
    def queryEpisodes(self, options):
        episodes = []
        query = "programSet(id:%d){title,path,synopsis,sharingUrl,image{url,url1X1,},items(orderBy:PUBLISH_DATE_DESC,filter:{isPublished:{equalTo:true}}first:%d){nodes{title,summary,synopsis,sharingUrl,publicationStartDateAndTime:publishDate,url,episodeNumber,duration,image{url,url1X1,},isPublished,audios{url,downloadUrl,mimeType,}}}}" % (int(self.id), options.latest)
        data = executeQuery(query)["data"]["programSet"]
        for item in data["items"]["nodes"]:
            episodes.append(AudiothekItem(0, item["title"], item["duration"], item["publicationStartDateAndTime"], item["audios"][0]["url"], sharingUrl=item["sharingUrl"], description=item["summary"], synopsis=item["synopsis"], imageUrl=item["image"]["url1X1"]))
        self.addItems(episodes)
        self.imageUrl = data["image"]["url1X1"]
        self.audiothekPath = data["path"]
        
    def toXML(self):
        channel = ET.Element('channel')
        showTitle = ET.SubElement(channel, 'title')
        showTitle.text = html.escape(self.title)
        showLink = ET.SubElement(channel, 'link')
        showLink.text = self.sharingUrl
        if self.imageUrl is not None:
            showImage = ET.SubElement(channel, "image")
            showImageUrl = ET.SubElement(showImage, "url")
            showImageUrl.text = html.escape(self.imageUrl)
            showImageTitle = ET.SubElement(showImage, "title")
            showImageTitle.text = html.escape(self.title)
            if self.audiothekPath is not None:
                showImageLink = ET.SubElement(showImage, "link")
                showImageLink.text = "https://www.ardaudiothek.de%s" % self.audiothekPath
        showDescription = ET.SubElement(channel, 'description')
        showDescription.text = html.escape(self.synopsis)
        atom = ET.SubElement(channel, "atom:link")
        atom.set("href", "ardaudiothek.html")
        atom.set("rel", "self")
        atom.set("type", "application/rss+xml")
        for item in self.items:
            if item.valid:
                channel.append(item.toXML())
        return channel

class AudiothekItem(object):
    
    def __init__(self, id, title, duration, dateTime, downloadUrl, sharingUrl="", description="", synopsis="", imageUrl=""):
        self.id = id
        self.title = title
        self.dateTime = "" if dateTime is None else dateTime
        self.duration = 0 if duration is None else duration
        self.downloadUrl = downloadUrl
        self.sharingUrl = sharingUrl if len(sharingUrl) > 0 else ""
        self.description = description if len(description) > 0 else ""
        self.synopsis = synopsis if len(synopsis) > 0 else ""
        self.valid = self.downloadUrl is not None
        self.imageUrl = imageUrl.replace("{width}", "448") if len(imageUrl) > 0 else None
        self.programSet = None
        
    def toXML(self):
        item = ET.Element('item')
        title = ET.SubElement(item, 'title')
        title.text = html.escape(self.title)
        description = ET.SubElement(item, 'description')
        description.text = html.escape(self.synopsis)
        guid = ET.SubElement(item, "guid")
        guid.text = self.sharingUrl
        link = ET.SubElement(item, "link")
        link.text = self.sharingUrl
        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", self.downloadUrl)
        enclosure.set("length", "")
        enclosure.set("type", "audio/mpeg")
        media = ET.SubElement(item, "media:content")
        media.set("url", self.downloadUrl)
        media.set("medium", "audio")
        media.set("type", "audio/mpeg")
        media.set("duration", str(self.duration))
        pubDate = ET.SubElement(item, "pubDate")
        pubDate.text = self.dateTime
        itunes = ET.SubElement(item, "itunes:duration")
        itunes.text = str(self.duration)
        if self.imageUrl:
            image = ET.SubElement(item, "image")
            imageUrl = ET.SubElement(image, "url")
            imageUrl.text = html.escape(self.imageUrl)
            imageTitle = ET.SubElement(image, "title")
            if self.programSet is not None:
                imageTitle.text = html.escape(self.programSet.title)
            itunesImage = ET.SubElement(item, "itunes:image")
            itunesImage.set("href", html.escape(self.imageUrl))
        return item

def executeQuery(query):
    url = "https://api.ardaudiothek.de/graphql"
    headers = {'Content-Type': 'application/json', 'Accept-Charset': 'UTF-8'}
    obj = {"query": "{%s}" % (query)}
    result = requests.post(url, json=obj, headers=headers)
    data = result.json()
    return data

def getCategories(options):
    categories = []
    if options.categoryID is None and options.categorySearch is None:
        return categories
    elif options.categoryID is not None:
        query = "editorialCategoriesByIDs(ids:[%s]){edges{node{title, id}}}" % (",".join(['"%s"' % str(categoryID) for categoryID in options.categoryID]))
    else:
        filter = '(filter:{title:{includes:"%s"}})' % options.categorySearch
        query = "editorialCategories%s{edges{node{title, id}}}" % filter
    data = executeQuery(query)["data"]["editorialCategories"]["edges"]
    for item in data:
        categories.append(AudiothekCategory(item["node"]["id"], item["node"]["title"]))
    return categories

def getProgramSets(options, categoryIDs):
    programSets = []
    filters = []
    offset = 0
    if len(categoryIDs) > 0:
        filters.append("editorialCategoryId:{in:[]}" % ",".join(['"%s"' % str(catID) for catID in categoryIDs]))
    if options.programSearch is not None:
        filters.append('title:{likeInsensitive:"%%%s%%"}' % options.programSearch)
    filter = ""
    if len(filters) > 0:
        filter = "filter:{%s}," % ",".join(filters)
    totalCount = -1
    while totalCount < 0 or offset + options.pagination <= totalCount:
        query = "programSets(%s,%s,orderBy:LAST_ITEM_ADDED_DESC){edges{node{title, id, sharingUrl, description, synopsis}}, totalCount}" % (filter, "first:%d,offset:%d" % (options.pagination, offset))
        data = executeQuery(query)["data"]
        if totalCount < 0:
            totalCount = data["programSets"]["totalCount"]
        for item in data["programSets"]["edges"]:
            programSet = AudiothekProgramSet(item["node"]["id"], item["node"]["title"], sharingUrl=item["node"]["sharingUrl"], description=item["node"]["description"], synopsis=item["node"]["synopsis"])
            programSets.append(programSet)
        offset += options.pagination
    return programSets

def getProgramSetsByID(options):
    query = "programSetsByIds(ids:[%s]){nodes{title, id, sharingUrl, description, synopsis}}" % (",".join(['"%s"' % str(showID) for showID in options.programID]))
    data = executeQuery(query)["data"]["programSetsByIds"]["nodes"]
    programSets = []
    for item in data:
        programSet = AudiothekProgramSet(item["id"], item["title"], sharingUrl=item["sharingUrl"], description=item["description"], synopsis=item["synopsis"])
        programSets.append(programSet)
    return programSets

def writeRSS(outputPath, root):
    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ", level=0)
    tree.write(outputPath, encoding="utf-8")

def queryContent(options):
    # create result var structure
    categories = []
    programSets = []
    
    # if programID filter is active directly query the programSet items
    if options.programID is not None:
        programSets.extend(getProgramSetsByID(options))
    else:
        categories.extend(getCategories(options))
        programSets.extend(getProgramSets(options, [cat.id for cat in categories]))
    return programSets

def main(options):
    # create the directory structure and output files
    htmlDir = os.path.join(options.outputDir, "html")
    rssDir = os.path.join(options.outputDir, "rss")
    if options.html and not os.path.exists(htmlDir):
        os.makedirs(htmlDir, exist_ok=True)
    if not os.path.exists(rssDir):
        os.makedirs(rssDir, exist_ok=True)
    
    # query the content
    limit = -1 if options.maxPrograms is None else options.maxPrograms
    count = 0
    stop = False
    jinjaVars = []
    programSets = queryContent(options)
    for programSet in programSets:
        programSet.queryEpisodes(options)
        if programSet.hasItems():
            root = ET.Element('rss')
            contentNode = programSet.toXML()
            root.append(contentNode)
            normTitle = unicodedata.normalize("NFKD", programSet.title)
            outputFileName = options.output % ("", int(programSet.id))
            outputPath = os.path.join(rssDir, outputFileName)
            writeRSS(outputPath, root)
            jinjaVars.append((os.path.join("..", "rss", outputFileName), normTitle))
            programSet.rssPath = outputPath
            programSet.items = None
            print("Written %d\t%s" % (int(programSet.id), programSet.title))
        count += 1
        if limit > 0 and count == limit:
            stop = True
        if stop:
            break
        if count % 100:
            sleep(1)
     
    if options.html:
        # order alphabetically
        programsByChar = {}
        for filePath, normTitle in jinjaVars:
            initChar = normTitle[:1].upper()
            if initChar not in programsByChar:
                programsByChar[initChar] = []
            programsByChar[initChar].append((filePath, normTitle))
        for initChar in programsByChar:
            programsByChar[initChar].sort(key=lambda x:x[1])
        letters = [("#%s" % html.escape(initChar.upper()), html.escape(initChar.upper())) for initChar in programsByChar]
        letters.sort(key=lambda x:x[1])
        orderedData = []
        for initChar, programSets in programsByChar.items():
            orderedData.append((html.escape(initChar.upper()), programSets))
        orderedData.sort(key=lambda x:x[0])
        
        # read template
        from jinja2 import Environment, FileSystemLoader
        templateDir = os.path.join(getScriptDirectory(), 'templates', 'standardissue')
        env = Environment(loader = FileSystemLoader(templateDir))
        template = env.get_template('index.jinja')
        htmlSource = template.render(orderedData = orderedData, 
                                     letters = letters, 
                                     date = datetime.today().strftime('%Y-%m-%d'), 
                                     args = " ".join(sys.argv[1:]))
        htmlOutputPath = os.path.join(htmlDir, "index.html")
        
        with open(htmlOutputPath, "w", encoding="utf8") as outf:
            outf.write(htmlSource)
            
        # copy other files of the template
        shutil.copytree(templateDir, htmlDir, dirs_exist_ok=True, ignore=shutil.ignore_patterns('index.jinja'))

def getScriptDirectory():
    return os.path.dirname(os.path.realpath(sys.argv[0]))
    
def getOptions(args=None):
    argParser = argparse.ArgumentParser()
    argParser.add_argument("--category-id", dest="categoryID", type=int, nargs="*", help="Audiothek category ID")
    argParser.add_argument("--category-search", dest="categorySearch", type=str, help="AUdiothek category search term")
    argParser.add_argument("--program-id", dest="programID", type=int, nargs="*", help="Audiothek program ID")
    argParser.add_argument("--program-search", dest="programSearch", type=str, help="Audiothek program search term")
    argParser.add_argument("--max-programs", dest="maxPrograms", type=int, help="Print the first n programs")
    argParser.add_argument("--pagination", type=int, default=100, help="Query at most this number of datasets at once")
    argParser.add_argument("--latest", type=int, default=10, help="Return only the last n items per program")
    argParser.add_argument("--html", action="store_true", default=False, help="create HTML overview of found items")
    argParser.add_argument("-d", "--directory", dest="outputDir", type=str, default="rss", help="base directory for HTML and RSS output files")
    argParser.add_argument("-o", "--output", dest="output", type=str, default="ardaudiothek_%s%d.rss", help="output RSS file name template")
    options = argParser.parse_args(args=args)
    
    # value checks
    if not os.path.exists(options.outputDir):
        sys.exit("The output directory %s does not exist" % options.outputDir)
    
    if options.programID is not None and (options.programSearch is not None or options.categoryID is not None):
        print("The --program-id argument overrides eventual restrictions by --program-search and --category-id.")
        options.search = None
        options.categoryID = None
    if "%d" not in options.output:
        lastDot = options.output.rfind(".")
        if lastDot > -1:
            options.output = options.output[:lastDot] + "%d" + options.output[lastDot:]
        else:
            options.output += "%d"
        print("The --output file name template has been corrected to %s" % options.output)
    
    return options
    

if __name__ == "__main__":
    main(getOptions(sys.argv[1:]))
