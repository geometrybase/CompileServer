# -*- coding: UTF-8 -*-
import tornado.web
import sys
import os
import time
import json
import requests
import subprocess

workingDir = ''
forwardUrl = ''

class UploadPyFileHandler(tornado.web.RequestHandler):
    def post(self):
        result = {}
        #result['msg'] = 'ok'

        strategyId = self.request.headers.get('strategyId')
        fileName = self.request.headers.get('fileName')
        fileExtension = self.request.headers.get('fileExtension').lower()
        access_token = self.request.headers.get('access_token')

        targetDir = os.path.join(workingDir, strategyId + '_' + time.strftime('_%Y%m%d%H%M%S', time.localtime()))
        if fileExtension == '.py':
            fileName = 'STR' + strategyId + fileExtension
        self._saveFile(targetDir, fileName, self.request.body)

        if fileExtension == '.py':
            result = _compilePyFile(targetDir, strategyId)
            if not result:
                result = self._forward(targetDir, strategyId, '.so', access_token)
        elif fileExtension == '.zip':
            result = _compileMFile(targetDir, strategyId, fileName)
            if not result:
                result = self._forward(targetDir, strategyId, '.zip', access_token)
        else:
            result = self._forward(targetDir, strategyId, fileExtension, access_token)

        self.write(result)

    def _saveFile(self, path, fileName, data):
        if not os.path.exists(path):
            os.makedirs(path)
        filepath = os.path.join(path, fileName)
        with open(filepath, 'wb') as upFile:
            upFile.write(data)

    def _forward(self, path, strategyId, fileExtension, access_token):
        headers = {'fileExtension': fileExtension, 'strategyId': strategyId, 'access_token': access_token}
        fileName = 'STR' +  strategyId + fileExtension
        filePathName = os.path.join(path, fileName)
        with open(filePathName, 'rb') as data:
            res = requests.post(forwardUrl, headers=headers, data=data)
            if res.status_code == 200 :
                 #result = json.dumps({"msg" : "success", "status" : 200})
                 result = res.content
            else:
                 result = '{"msg" : "upload error", "status" :"'+ str(res.status_code) +'"}'
            return result

def _compilePyFile(path, strategyId):
    # compile py file
    cmdStr = 'python -c ' + \
             '"from distutils.core import setup;' + \
             ' from Cython.Build import cythonize;' + \
             ' setup(ext_modules = cythonize(\'STR' + strategyId + '.py\'))"' + \
             ' build_ext --inplace'
    proc = subprocess.Popen(cmdStr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=path)

    errorStr = ""
    line = "start"
    collectMessage = False

    while line:
        if line.startswith('Error compiling '):
            errorStr = 'Failed to compile strategy file:\n'
            collectMessage = True #start collect error message
        elif collectMessage and line.startswith('Traceback '):
            collectMessage = False #stop collect error message
        else:
            if collectMessage:
                errorStr += line

        line = proc.stdout.readline()
        print ">> ", line, #line has \n, so no need to switch line in print

    print #switch line after all printed

    retStr = None
    if errorStr:
        retStr = json.dumps({'msg':errorStr, 'status':500})
    return retStr

def _compileMFile(path, strategyId, fileName):
    errorStr = "matlab compile error"
    
    # compile m file
    mcompile = "matlab  -nojvm -nodisplay -nosplash -nodesktop -r 'pcode *.m, exit'"
    finalFileName = 'STR' + strategyId + '.zip'

    # chdir
    ret = os.chdir(path)

    # unzip
    cmdStr = 'unzip -o ' + fileName
    ret = ret or os.system(cmdStr)
    
    # rename
    if fileName[:-4] != 'Main':
        cmdStr = 'mv -f ' + fileName[:-4] + '.m Main.m'
        ret = ret or os.system(cmdStr)
    
    # compile *.m to *.p
    cmdStr = mcompile
    ret = ret or os.system(cmdStr)
    
    # zip
    cmdStr = 'zip ' + finalFileName + ' *.p'
    ret = ret or os.system(cmdStr)
    print ret    
    # remove tmp files
    cmdStr = 'rm -rf *.m *.p'
    ret = ret or os.system(cmdStr)

    retStr = None
    if ret:
        retStr = json.dumps({'msg':errorStr, 'status':500})
    return retStr
