import sys
import requests
import re
import os
import urllib
from bs4 import BeautifulSoup
from enum import IntEnum

class FILE_ATTRIBUTES(IntEnum):
    FILE_ATTRIBUTES_UNKNOW = 0
    FILE_ATTRIBUTES_FOLDER = 1
    FILE_ATTRIBUTES_FILE   = 2
    FILE_ATTRIBUTES_PARENT = 3

class FindData:
    def __init__(self):
        self.attributes = 0
        self.name = ""
        self.size = 0
        self.link = ""
        self.parent = ""

class FindFile:
    def __init__(self,url):
        self.header={'Host': 'mirrors.sohu.com',
           'Upgrade-Insecure-Requests': '1',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
        }
        self.url = url
        self.number = 0
        self.idx = 0

        html = requests.get(self.url,headers=self.header)
        self.tr = BeautifulSoup(html.text,'html5lib').find_all('tr')
        self.number = len(self.tr)

    def GetObj(self,idx):
        data = FindData()
        tr = self.tr
        if idx >= self.number:
            return None

        obj = tr[idx]
        if not obj or not obj.contents[0] or not obj.contents[0].contents[0]:
            return None

        data.name = obj.contents[0].text.replace('/','')
        data.link = obj.contents[0].contents[0]['href']
        data.parent = self.url
        size = obj.contents[1].text.strip()
        if size == '-':
            data.size = 0
            if -1 != data.name.find("Parent directory"):
                data.attributes = FILE_ATTRIBUTES.FILE_ATTRIBUTES_PARENT
            else:
                data.attributes = FILE_ATTRIBUTES.FILE_ATTRIBUTES_FOLDER
        else:
            data.attributes = FILE_ATTRIBUTES.FILE_ATTRIBUTES_FILE
            digital = size.split()[0]
            unit = size.split()[1]
            if unit[0] == 'K':
                data.size = int(float(digital) * 1024)
            elif unit[0] == 'M':
                data.size = int(float(digital) * 1024 * 1024)
            elif unit[0] == 'G':
                data.size = int(float(digital) * 1024 * 1024 * 1024)
            else:
                data.size = int(digital)
        return data

    def FirstFile(self):
        self.idx = 1
        return self.GetObj(self.idx)

    def NextFile(self):
        self.idx += 1
        return self.GetObj(self.idx)

def GetAllSize(data):
    if(not hasattr(GetAllSize,'size')):
        GetAllSize.size = 0
    GetAllSize.size = GetAllSize.size + data.size

def SyncFile(data):
    localdir="/mnt/fedora29"
    parsed = urllib.parse.urlparse(data.parent)
    localdir = localdir + parsed.path
    if not os.path.exists(localdir):
        os.system("mkdir -p " + localdir)

    print("Downloading... url = " + data.parent + data.link + " , size = " + str(data.size/1024) + " KB")
    r = requests.get(data.parent + data.link)
    with open(localdir+data.name,"wb") as f:
        f.write(r.content)

def EnumerateFileInDirectory(url,recursion,fn=None,exclude=None):
    find = FindFile(url)
    data = find.FirstFile()
    while data is not None:
        if recursion and data.attributes == FILE_ATTRIBUTES.FILE_ATTRIBUTES_FOLDER and data.name not in exclude:
            EnumerateFileInDirectory(url+data.link,recursion,fn,exclude)
        elif fn is not None and data.attributes == FILE_ATTRIBUTES.FILE_ATTRIBUTES_FILE:
            fn(data)
        data = find.NextFile()
       
if __name__ == "__main__":
    exclude = ['Cloud','Container','Silverblue','Spins','armhfp','iso','aarch64']
    #EnumerateFileInDirectory("https://mirrors.sohu.com/fedora/releases/29/",True,GetAllSize,exclude)
    #EnumerateFileInDirectory("https://mirrors.sohu.com/fedora/updates/29/",True,GetAllSize,exclude)

    EnumerateFileInDirectory("https://mirrors.sohu.com/fedora/releases/29/",True,SyncFile,exclude)
    EnumerateFileInDirectory("https://mirrors.sohu.com/fedora/updates/29/",True,SyncFile,exclude)
