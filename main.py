import sys
import requests
import re
import os
import time
import platform
import threading
from concurrent.futures import ThreadPoolExecutor
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
        while html.status_code != 200:
            time.sleep(1)
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
            if unit == 'KiB':
                data.size = int(float(digital) * 1024)
            elif unit == 'MiB':
                data.size = int(float(digital) * 1024 * 1024)
            elif unit == 'GiB':
                data.size = int(float(digital) * 1024 * 1024 * 1024)
            elif unit == 'B':
                data.size = int(digital)
            else:
                data.size = 0
        return data

    def FirstFile(self):
        self.idx = 1
        return self.GetObj(self.idx)

    def NextFile(self):
        self.idx += 1
        return self.GetObj(self.idx)

class SpiderDownload:
    def __init__(self,urls,exlude_dir=[""]):
        self.all_size = 0
        self.download_size = 0
        self.exlude_dir = exlude_dir
        self.urls = urls
        self.tp_num = 10
        self.tp = ThreadPoolExecutor(self.tp_num)

        self.lock = threading.Lock()
        self.RLock = threading.RLock()
        self.AllSizeCnt = 0
        self.DownloadCnt = 0
        self.threadcnt = 0
        self.DownloadedCnt = 0

        self.header={'Host': 'mirrors.sohu.com',
           'Upgrade-Insecure-Requests': '1',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
        }


    def _DoGetAllSize(self,data):
        with self.lock:
            self.all_size = self.all_size + data.size
        return 0

    def GetAllSize(self,recursion):
        for url in self.urls:
            self._EnumerateFileInDirectory(url,recursion,self._DoGetAllSize)

    def _DoDownloadFile(self,data):
        with self.lock:
            self.threadcnt = self.threadcnt + 1
            print(self.threadcnt,self.DownloadCnt,self.DownloadedCnt,self.AllSizeCnt)

        try:
            localdir="E:/Fedora29"
            parsed = urllib.parse.urlparse(data.parent)
            localdir = localdir + parsed.path
            if not os.path.exists(localdir):
                if platform.system() == "Windows":
                    command = "mkdir " + localdir.replace("/","\\")
                else:
                    command = "mkdir -p " + localdir
                os.system(command)

            print("Downloading... " + str(round(self.download_size/1024/1024,2)) + "/" + str(round(self.all_size/1024/1024,2)) + " MB " + data.parent + data.link + "," + str(round(data.size/1024,2)) + "KB")
            if not os.path.exists(localdir+data.link):
                html = requests.get(data.parent + data.link,headers=self.header)
                while html.status_code != 200:
                    time.sleep(1)
                    html = requests.get(data.parent + data.link,headers=self.header)
                with open(localdir+data.link,"wb") as f:
                    f.write(html.content)

            with self.lock:
                self.download_size = self.download_size + data.size

        except Exception as result:
            print("ERROR: Download " + data.parent + data.link + " error, " + str(result))

        finally:
            with self.lock:
                self.DownloadedCnt = self.DownloadedCnt + 1
                self.threadcnt = self.threadcnt - 1

        return 0

    def DownloadFile(self,recursion):
        if self.all_size == 0:
            self.GetAllSize(recursion)

        for url in self.urls:
            self._EnumerateFileInDirectory(url,recursion,self._DoDownloadFile)

    def _EnumerateFileInDirectory(self,url,recursion,fn=None):
        find = FindFile(url)
        data = find.FirstFile()
        while data is not None:
            if recursion and data.attributes == FILE_ATTRIBUTES.FILE_ATTRIBUTES_FOLDER and data.name not in self.exlude_dir:
                self._EnumerateFileInDirectory(url+data.link,recursion,fn)
            elif fn is not None and data.attributes == FILE_ATTRIBUTES.FILE_ATTRIBUTES_FILE:
                if fn == self._DoGetAllSize:
                    with self.lock:
                        self.AllSizeCnt = self.AllSizeCnt + 1
                    fn(data)
                else:
                    self.RLock.acquire()
                    while self.DownloadCnt - self.DownloadedCnt > 200:
                        time.sleep(1)
                    self.RLock.release()

                    with self.lock:
                        self.DownloadCnt = self.DownloadCnt + 1
                    self.tp.submit(fn,data)

            data = find.NextFile()

if __name__ == "__main__":
    exclude = ['Cloud','Container','Silverblue','Spins','armhfp','iso','aarch64','source','images','isolinux','EFI']
    sd = SpiderDownload(["https://mirrors.sohu.com/fedora/releases/29/","https://mirrors.sohu.com/fedora/updates/29/"],exclude)
    st = int(time.time())
    sd.GetAllSize(True)
    print("sd.GetAllSize: " + str(sd.all_size) + "/" + str(sd.AllSizeCnt))
    et = int(time.time())
    print("take: " + str(int((et-st)/60)) + ":" + str(int(et-st)%60))

    st = int(time.time())
    sd.DownloadFile(True)
    et = int(time.time())
    print("take: " + str(int((et-st)/60)) + ":" + str(int(et-st)%60))




















