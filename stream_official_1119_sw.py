# from insert import insert_data
# from elasticsearch import helpers
import datetime
import json

try:
    import ujson
    import orjson
except:
    import json as ujson
    import json as orjson
# import re
try:
    import regex as re
except:
    import re
# import orjson as json
import uuid
from copy import deepcopy

import geoip2.database
from urllib import parse
import sys
import base64
import time
import html

import sys

sys.path.append("/opt/openfbi/pylibs")
# from key_sen_Identify import sentivite_identify
# from Raway_custom import *
from field_match import *
from unix_utils import *

# 2022年6月23日10:58:07  使用length字段代替content_length字段表示流量

# sys.path.append('/home/zhds/.local/lib/python3.6/site-packages/')
# import os
# os.environ['JAVA_HOME'] = '/opt/jdk1.8.0_162'
# from pyhanlp import HanLP

# segment = HanLP.newSegment().enableNameRecognize(True)  # 构建人名识别器
# modify --lhq  修改 访问函数 把原流量中的请求体和响应体base64解码展示  删除gmt_create、creator等字段

def sensite_data(response_body, sen, op, areas_content, err_name):
    """
    :param response_body:
    :param sen:{data:[{正则匹配，关键字}]}
    :return: 字符串:[身份证，手机号，邮箱，地址]
    """
    # rzc by  info
    info = {}
    #

    key1 = []
    keya = []
    index = op.get('index')
    data = op.get('data')
    tu = {}
    sens = []
    if response_body:
        for i in range(len(index)):
            tu[data[i][0]] = index[i]
        sen1 = sen.get('data')
        for item in sen1:
            name = item.get('name').replace('\\\\', '\\')
            rekey = item.get('rekey')
            is_t = re.findall(r'%s' % name, response_body)
            # add by rzc
            if rekey == "姓名":
                info[rekey] = is_t
                continue
            if rekey == "地址":
                info[rekey] = is_t
                continue
            if is_t:
                sens.append(list(set(is_t)))
                key = tu.get(rekey)
                keya.append('%s' % rekey)
                key1.append('%s' % key)
        # add by rzc 2022/11/25
        info = name_address(info, areas_content, err_name)
        for rekey, is_t in info.items():
            if is_t:
                sens.append(list(set(is_t)))
                key = tu.get(rekey)
                keya.append('%s' % rekey)
                key1.append('%s' % key)
        #
    if key1:
        key1 = json.dumps(key1, ensure_ascii=False)
    else:
        key1 = ""
    return key1, keya, sens


def name_address(info, areas_content, err_name):
    """
    :param info: 姓名地址敏感数据
    :param areas_content: 地址csv文件
    :param n_name: 错误姓名csv文件
    :return: info 过滤后的姓名地址敏感数据
    """
    name_list, address_list = [], []
    names = info["姓名"]
    if names != []:
        for name in names:
            if name not in areas_content:
                name_list.append(name)
            else:
                address_list.append(name)
        # 在对name_list进行筛选一些常见的名称
        name_list = [name for name in name_list if name not in err_name]
        info["姓名"] = name_list
        info["地址"].extend(address_list)
    return info


def handle_content_type(content):
    """
    #从参数配置json对象中取出新增的资源类型 格式: {
                 "name": "Host",
                 "value": "archive.ubuntu.com"}
        需要转换成 {"host":archive.ubuntu.com}格式
    """
    content_type = {"text/html": "HTML",
                    "text/plain": "JSON",
                    "text/xml": "XML",
                    "image/gif": "资源文件",
                    "image/jpeg": "资源文件",
                    "image/png": "资源文件",
                    "image/wxpic": "资源文件",
                    "image/x-icon": "资源文件",
                    "image/webp": "资源文件",
                    "image/bmp": "资源文件",
                    "image/jpg": "资源文件",
                    "text/css": "CSS",
                    "image/pjpeg": "资源文件",
                    "image/x-png": "资源文件",
                    "application/javascript": "JS",
                    "application/x-javascript": "JS",
                    "text/javascript": "JS",
                    "text/octet": "数据文件",
                    "text/json": "JSON",
                    "application/xhtml\+xml": "HTML",
                    "application/multipart-formdata": "数据文件",
                    "application/font-woff": "资源文件",
                    "application/x-debian-package": "资源文件",
                    "multipart/form-data": "数据文件",
                    "text/csv": "数据文件",
                    "application/x-7z-compressed": "数据文件",
                    "binary/octet-stream": "数据文件",
                    "image/svg\+xml": "数据文件",
                    "application/x-gzip": "数据文件",
                    "font/woff": "资源文件",
                    "Image/png": "资源文件",
                    "image/vnd.microsoft.icon": "资源文件",
                    "text/html, text/html": "HTML",
                    "application/x-www-form-urlencoded": "数据文件",
                    "application/pdf": "数据文件",
                    "application/x-protobuf": "数据文件",
                    "application/zip": "数据文件",
                    "application/force-download": "数据文件",
                    "application/xml": "XML",
                    "application/json": "JSON",
                    "application/octet-stream": "数据文件",
                    "video/mp4": "资源文件",
                    "application/soap\+xml": "XML",
                    "application/ocsp-response": "HTML",
                    "application/vnd.ms-cab-compressed": "HTML", }
    dic = {}
    if content:
        for dicts in content:
            value = list(dicts.values())
            dic.setdefault("{}".format(value[0]), "{}".format(value[1]))
        if dic:
            content_type = dict(content_type, **dic)
        return content_type


def handle_url(element, hostname, uri, dest_port, content_type):
    """
    param:element:流量
    param:hostname:应用
    param:uri:流量中url字段表接口路径
    param:dest_port:流量内容中服务器ip数据
    param:content_type:内容类型
    content:对接口进行拼接 加接口去重 去重逻辑详见 乔晗
    """
    if uri and '?' in uri:
        # 剔除参数
        suri = uri.split('?')
        uri = suri[0]
        parameter = suri[1]
    else:
        uri = uri
        parameter = ''
    splits = re.split(r'/', uri)
    https = element.get('http')
    data_type = "未知"
    ht_type = https.get('http_content_type')
    if ht_type:
        for i in range(len(content_type)):
            if list(content_type.keys())[i] in ht_type:
                a = re.findall(r'%s' % list(content_type.keys())[i], ht_type)
                data_type = content_type[a[0]]
                break
    else:
        data_type = "未知"
    if data_type != 'JSON' and data_type != 'XML' or (splits[-1] and '.' in splits[-1]):
        if splits[-1] and '.' in splits[-1] and len(splits) > 2:
            find = re.findall(r'\.[a-zA-Z]+', splits[-1])
            if find:
                uri_c = '/' + splits[1] + '/{dst}'
        elif splits[-1] and '.' in splits[-1] and len(splits) <= 2:
            find = re.findall(r'\.[a-zA-Z]+', splits[-1])
            if find:
                uri_c = '/{dst}'
        elif data_type == '资源文件' and len(splits) > 2:
            uri_c = '/' + splits[1] + '/{dst}'
        elif data_type == '资源文件' and len(splits) <= 2:
            uri_c = '/{dst}'
        else:
            try:
                n = uri.rindex('/')
                uri_c = uri[0:n] + '/{dst}'
                if n == 0:
                    uri_c = uri
            except:
                # print("error:", uri)
                uri_c = uri
    else:
        uri_c = uri
    if dest_port == '80':
        try:
            url_c = "http://" + hostname + uri_c
            url = "http://" + hostname + uri
        except Exception as e:
            url_c = "http://" + hostname
            url = "http://" + hostname
    else:
        try:
            url_c = "http://" + hostname + ':' + dest_port + uri_c
            url = "http://" + hostname + ':' + dest_port + uri
        except Exception as e:
            url_c = "http://" + hostname + ':' + dest_port
            url = "http://" + hostname + ':' + dest_port
    return [url, url_c, data_type, parameter]


def handle_login(login):
    """
    :param login:
    :return:
    :time 2022年4月17日18:48:43
    从产品中拿到的验证登录的字典数据，转换成列表形式
    """
    # loginls = ['username', 'userid', 'account', 'loginid', 'loginname', 'user', 'email', 'phone', 'phpsessid',
    #            'token', 'jsessionid']
    login_list = []
    if login:
        for log in login:
            name = log["name"]
            login_list.append(name)
    lo_list = list(set(login_list))
    return lo_list


def handle_account(account):
    """
    param:account 产品中账户检索的字典数据
    content：将字典类型的数据转换为列表形式
    """
    # loginls = ['userName', 'userid', 'account', 'loginid', 'loginname', 'email', 'phone']
    account_list = []
    if account:
        for ac in account:
            for av in ac.values():
                account_list.append(av)
    ac_list = list(set(account_list))
    return ac_list


def handle_risk_on_off(on_off):
    """
    param:on_off 产品中风险开关的字典数据
    content:将字典类型 数据转换为列表
    """
    onlist = []
    for on in on_off.values():
        onlist.append(on)
    return onlist


def handle_lan(network):
    """
    param:network:产品中地域解析的字典数据
    content：将字典数据添加进lans列表中
    """
    lans = ['192.168', '10.', '172.16']
    for net in network:
        lans.append(net['name'])
    lans = list(set(lans))
    return lans


def handle_flag(tag):
    """
    param:tag:产品中定义标签数据
    content：将数据格式化
    """
    d_flag = {}
    for flag in tag:
        value = list(flag.values())
        d_flag.setdefault("{}".format(value[0]), "{}".format(value[1]))
    return d_flag


def http_apis(https, timestamp, dstip, destport, url_c, hostname, data_type, api_type, token_rule, ak_rule):
    """
    :param element: kafka 含http数据
    :param api_list: 去重列表
    :param loginls :["login"]
    :param logoutls:["logout"]
    :param downloadls:["download"]
    :param uploadls:["upload"]
    :param onlist 风险开关列表
    :param sen
    :param op
    :return:
    :content:接口处理函数 包括风险识别、敏感识别、内容类型映射等功能返回字典存放接口数据；详见乔晗
    """
    http_new = {}
    # https = element.get('http')
    method = https.get('http_method')
    http_new['url'] = url_c
    # http_new['gmt_create'] = datetime.datetime.now()
    # http_new['gmt_modified'] = datetime.datetime.now()
    # http_new['creator'] = 'all'
    # http_new['owner'] = 'all'
    http_url = https.get('url')
    if http_url and '?' in http_url:
        api = http_url.split('?')
        http_uri = api[0]
        parameter = api[1]
    else:
        http_uri = http_url
        parameter = ''
    http_new['parameter'] = parameter
    http_new['api'] = http_uri
    name = ''
    try:
        n = http_uri.rindex('/')
        name = http_uri[n + 1:]
        if n == 0:
            name = http_uri
    except:
        name = http_uri
    http_new['name'] = name
    # if hostname.startswith('10.') or hostname.startswith('192.168') or hostname.startswith('172.16'):
    #     # 1 局域网
    #     # 192.168
    #     # 172.16
    #     http_new['app_type'] = 1
    # elif hostname.startswith('127.0.0.1'):
    #     # 2.本机
    #     http_new['app_type'] = 2
    # else:
    #     # 3.互联网
    #     http_new['app_type'] = 0
    http_new['app_type'] = 1
    http_new['protocol'] = https.get('protocol')
    if hostname == "127.0.0.1" or not hostname:
        hostname = dstip
    http_new['app'] = hostname
    http_new['dstport'] = destport
    http_new['dstip_num'] = 1
    http_new['account_num'] = 1
    http_new['srcip_num'] = 1
    http_new['first_time'] = timestamp
    http_new['last_time'] = timestamp
    http_new['method'] = method
    http_new['data_type'] = data_type
    request_headers = https.get('request_headers')
    # api_type 接口类型 普通(默认):0;登录:1;含有敏感数据接口:2;文件上传:3;文件下载:4;服务接口:5;数据库操作:6; 检测url
    # url_login = 0  # 登录或非登录-状态
    # http_url = https.get('url')
    # cookie = https.get('cookie')
    #
    # 0 - 普通，1 - 登录，2 - 上传，3 - 下gent_ip.append(srcip)载，4-注销，5 - 服务接口，6 - 数据库操作，7 - 命令操作
    # api_type = 0
    # if http_url:  # 逻辑顺序更改,辨别方式更改
    #     if cookie:  # 判断方法更改
    #         for item in loginls:#
    #
    #             if item in cookie or 'login' in http_url:
    #                 api_type = 1
    #                 url_login = 1
    #                 break
    #     else:
    #         cookie = ''
    #     # 如果接口类型是普通，继续识别其他类型。如果是登录，停止 ;下面逻辑只判断一种可能，后续继续补充添加。
    #     # 此乃初级版 改动于2022年4月17日18:47:54
    #
    #     if not url_login and logoutls[0] in http_url:
    #         # 注销类型
    #         api_type = 8
    #     elif url_login and 'login' in http_url:
    #         api_type = 1
    #         # if 'upload' in http_url or (http_new['data_type'] == '资源文件' and method == 'POST'):
    #         # 上传类型
    #     request_headers = https.get('request_headers')
    #     if uploadls and method == 'POST' and request_headers:
    #         for req in request_headers:
    #             if "name" in req:
    #                 if req['name'] == "content-type":
    #                     for item in uploadls:
    #                         if item in req['value']:
    #                             api_type = 3
    #                             break
    #                     break
    #     #if uploadls[0] in http_url or (http_new['data_type'] == '资源文件' and method == 'POST'):
    #     #    api_type = 3
    #     # 下载类型
    #     if (downloadls[0] in http_url and data_type!="资源文件")  or (http_new['data_type'] == '数据文件' and method == 'GET'):
    #         api_type = 4
    #     # 服务接口
    #     elif data_type == 'JSON' or data_type == 'XML':
    #         # 5.服务接口
    #         api_type = 5
    # 判断数据接口的认证类型  1-basic认证  2-签名认证  3-soap认证  4-token认证  5-cookie认证
    # 初始化
    # auth_type = 0
    # if api_type == 5:
    #     # 数据接口响应状态为2开头的
    #     if str(https.get('status'))[:1] == "2":
    #         have_auth = False
    #         token_rule = '(?:^|&)(?:' + token_rule + ')=([^&]*)'
    #         ak_rule = '(?:^|&)(?:' + ak_rule + ')=([^&]*)'
    #         basic_rule = "(?<=https://)([\w\W]*:[\w\W]*)(?=@)"
    #         soap_rule = "<(soap|soapenv):Envelope[\w\W]*<(soap|soapenv):Body"
    #         if re.findall(token_rule, parameter):
    #             # token认证
    #             have_auth = True
    #             auth_type = 4
    #         if not have_auth or re.findall(ak_rule, parameter):
    #             # 签名认证
    #             have_auth = True
    #             auth_type = 2
    #         if not have_auth:
    #             # soap认证
    #             http_request_body = https.get('http_request_body', "")
    #             if http_request_body:
    #                 if re.findall(soap_rule, http_request_body):
    #                     have_auth = True
    #                     auth_type = 3
    #         if not have_auth:
    #             # basic认证
    #             # 解析request_headers中的内容并判断是否含有basic认证
    #             if request_headers:
    #                 req_name = []
    #                 for req in request_headers:
    #                     req_name.append(req['name'])
    #             if req_name:
    #                 if "authorization" in req_name:
    #                     have_auth = True
    #                     auth_type = 1
    #         if not have_auth or re.findall(basic_rule, url_c):
    #             # basic认证
    #             have_auth = True
    #             auth_type = 1
    #         if not have_auth:
    #             # cookie认证
    #             if req_name:
    #                 if "cookie" in req_name:
    #                     have_auth = True
    #                     auth_type = 5

    # 接口状态 0 未监控 1 监控   0 未审计 1 审计
    http_new['api_type'] = api_type
    http_new['api_status'] = 0
    # 数据接口认证类型
    #http_new['auth_type'] = auth_type

    # 风险标签
    http_new['risk_label'] = ''
    http_new['risk_level'] = 0
    http_new['risk_label_value'] = ''
    http_new['visits_num'] = 1
    http_new['visits_flow'] = https.get('length', 0)
    http_new['res_llabel'] = ''
    http_new['req_label'] = ''
    http_new['sensitive_label'] = '0'
    # return http_new, api_type
    return http_new

'''
def api_types(http, data_type, loginls, logoutls, downloadls, uploadls):
    https = http.get('http', '')
    url = https.get('url')

    url_list = url.split("?")
    if len(url_list) == 2:
        paramter = url_list[-1]
        http_url = url_list[0]
    else:
        http_url = url
        paramter = ""
    cookie = https.get('cookie', '')
    Authorization = https.get('Authorization', '')
    # 请求方式
    method = https.get('http_method', '')
    request_headers = https.get('request_headers', '')
    response_headers = https.get('response_headers', '')
    request_body = http.get('http_request_body', '').lower()
    response_body = http.get('http_response_body', '').lower()

    # -----开始判断----
    # 0-其他 1-登陆 3-上传 4-下载 5-服务 8-注销
    api_type = 0
    # 判断请求是否是POST
    if method == "POST":
        # 判断是否是上传接口
        # 判断Content-Type中是否含有‘multipart/form-data’和‘binary/octet-stream’
        header_ok = 0
        for header in request_headers:
            if header.get('name', '').lower() == 'content-type':
                for i in ['multipart/form-data', 'binary/octet-stream']:
                    if i in header['value']:
                        header_ok = 1
                        break
                else:
                    continue
                break
        # 将“空”加入列表中，代表该功能暂未启用
        if header_ok:
            for i in ['', 'upload']:
                if i in url:
                    api_type = 3

    # 判断是否是登陆接口
    # 4个OK条件同时满足3个即可
    login_ok = 0
    url_ok = 0
    # 判断url是否满足条件
    for i in ["login", "auth", "logon", "sign", "token"]:
        if i in url:
            url_ok = 1
            login_ok += 1
            break
    # 判断user/password关键字是否符合条件
    u_p_ok = 0
    for i in ["passwd", "password", "pwd", "psw", "pass", "key"]:
        if i in request_body or i in url:
            for j in ["account", "loginuser", "loginname", "name", "userid", "phone", "mobile", "loginid", "user"]:
                if j in request_body or j in url:
                    u_p_ok = 1
                    login_ok += 1
                    break
            else:
                continue
            break

    # 判断登陆返回结果是否有成功或失败
    if u_p_ok and url_ok:
        for i in ["成功", "success", "失败", "错误", "fail", 'true', 'error', 'suc', '"code": 200', '"code": 1', '"code": 400',
                  '"code": 0']:
            if i in response_body:

                login_ok += 1
                break

    # 判断响应头中有session 或者 请求头中是否含有关键字
    re_header = 0
    for res_header in response_headers:
        if res_header and res_header.get('name') and res_header.get('value'):
            lower_res_header = res_header.get('name', '').lower()
            if 'set-cookie' in lower_res_header:
                for i in ["session", "token", "auth", "appid", "deviceid", "ticket", "client_key", "lid","grafana_remember", "sessid", "grafana_sess", "clientid"]:
                    if i in res_header.get('value'):

                        re_header = 1
                        login_ok += 1
                        break
                else:
                    continue
                break
    # 判断响应体中是否含有认证的关键字
    if not re_header:
        for i in ["session", "token", "ticket", "client_key",
                  "grafana_remember", "sessid", "grafana_sess", "clientid"]:
            if i in response_body:

                re_header = 1
                login_ok += 1
                break
    # 判断请求头中是否有认证的关键请求头
    if not re_header and url_ok:
        for req_header in request_headers:
            lower_req_header = req_header.get('name', '').lower()
            for i in ['authorization', 'cookie']:
                if i in lower_req_header:
                    login_ok += 1
                    break
            else:
                continue
            break
    # 4个条件满足3个即可
    if login_ok >= 3:
        api_type = 1

    # 判断是否是下载接口
    for res_header in response_headers:
        if res_header.get('name', '').lower() == 'content-disposition':
            api_type = 4
            break

    # 判断是否是注销接口
    if data_type != "资源文件" and data_type != "CSS" and data_type != "JS":
        for item in logoutls:
            if item in http_url:
                # 注销类型
                api_type = 8
                break
    # 判断是否是服务接口--首先该服务接口不能是其他类型的接口
    if api_type == 0 and (data_type == 'JSON' or data_type == 'XML'):
        api_type = 5


    # ===============gent_ip.append(srcip)老版本代码==============
    # if http_url:  # 逻辑顺序更改,辨别方式更改
    #     # if cookie:  # 判断方法更改
    #     #     for item in loginls:  #
    #     #         if (item in cookie or 'login' in http_url) and method=="POST":
    #     #             api_type = 1
    #     #             url_login = 1
    #     #             break
    #     # else:
    #     #     cookie = ''
    #
    #     # 如果接口类型是普通，继续识别其他类型。如果是登录，停止 ;下面逻辑只判断一种可能，后续继续补充添加。
    #     # 此乃初级版 改动于2022年4月17日18:47:54
    #
    #
    #     # elif url_login and 'login' in http_url:
    #     #     api_type = 1
    #     # if 'upload' in http_url or (http_new['data_type'] == '资源文件' and method == 'POST'):
    #     # 上传类型
    #     request_headers = https.get('request_headers')
    #     if uploadls and method == 'POST' and request_headers:
    #         for req in request_headers:
    #             if "name" in req:
    #                 if req['name'] == "content-type":
    #                     for item in uploadls:
    #                         if item in req['value']:
    #                             api_type = 3
    #                             break
    #                     break
    #     # if uploadls[0] in http_url or (http_new['data_type'] == '资源文件' and method == 'POST'):
    #     #    api_type = 3
    #     # 下载类型
    #     if (downloadls[0] in http_url and data_type != "资源文件") or (
    #             data_type == '数据文件' and (method == 'GET' or method == 'POST')):
    #         api_type = 4
    #     # 服务接口
    #     elif data_type == 'JSON' or data_type == 'XML':
    #         # 5.服务接口
    #         api_type = 5
    #     if method == "POST":
    #         for item in loginls:
    #             if http_url.endswith(item):
    #                 if cookie or Authorization:
    #                     api_type = 1
    #                     url_login = 1
    #                     break
    #         # if paramter:
    #         #    if "username" in paramter or "password" in paramter or "email" in paramter or "grant_type" in paramter:
    #         #        api_type = 1
    return api_type
'''

GeoLite = geoip2.database.Reader('/opt/openfbi/fbi-bin/lib/GeoLite2-City.mmdb')


def http_op(timestamp, srcip, length, http_user_agent, lans, flags, request_headers):
    """
    :param element: kafka 含http数据
    :param ip_list: 去重列表
    :return:
    :flags : {'127.0.0.1': '开发标签', '192.168': '飞龙在天'}
    :lans : ['192.168', '10.', '172.16']
    :content:终端从处理函数 从流量中解析字典 返回字典
    """
    http_ips = {}
    # http = element.get('http')
    http_ips['firsttime'] = timestamp
    http_ips['lasttime'] = timestamp
    # http_ips['gmt_create'] = datetime.datetime.now()
    # http_ips['gmt_modified'] = datetime.datetime.now()
    # http_ips['creator'] = 'all'
    # http_ips['owner'] = 'all'
    http_ips['srcip'] = srcip
    # src_ip = element.get('src_ip')
    # 地域 根据src_ip 分析
    # for lan in lans:
    #     bool_lan = 0
    #     if lan in http_ips['srcip']:
    #         bool_lan = 1
    #         break
    #
    # if bool_lan:
    #     http_ips['region'] = '局域网'
    # else:
    #     try:
    #         response = GeoLite.city(http_ips['srcip'])
    #         http_ips['region'] = response.city.names["zh-CN"]
    #     except:
    #         http_ips['region'] = '未知'
    # network = re.findall(r'(.*\.)', http_ips['srcip'])  # 正则添加网段
    # try:
    #     network = re.sub(r'\.$', '.0', network[0])
    # except:
    #     network = ''
    http_ips['network'] = ""
    http_ips['account_num'] = 1
    http_ips['api_num'] = 1
    http_ips['app_num'] = 1
    http_ips['visit_num'] = 1
    http_ips['visit_flow'] = length
    hostname = srcip
    # if hostname in flags.keys():
    #    http_ips['flag'] = flags[hostname]
    # if hostname == '127.0.0.1':
    #     http_ips['flag'] = '开发标签'
    # 终端类型,pc或者java程序 需判断 user_agent?
    user_agent = http_user_agent
    if user_agent != '':
        http_ips['flag'] = user_agent
        if 'Mozilla' in user_agent or 'Opera' in user_agent and 'Windows' in user_agent or 'Linux' in user_agent or 'Mac' in user_agent:
            http_ips['type'] = 'PC'
        elif 'iPhone' in user_agent or 'Android' in user_agent:
            http_ips['type'] = 'MOBILE'
        elif 'Opera' not in user_agent or 'Mozilla' not in user_agent or 'Nikto' in user_agent or 'Nmap' in user_agent or 'Googlebot' in user_agent:
            http_ips['type'] = '其他'
    else:
        http_ips['type'] = '其他'
    # http_ip_list 列表
    realip, agent_ip = real_ip(request_headers, srcip)
    http_ip_list = []
    if realip != '':
        http_ips1 = http_ips.copy()
        http_ips1['type'] = 'XFF'
        http_ips1['srcip'] = realip
        http_ip_list.append(http_ips1)
    if agent_ip:
        for i in agent_ip:
            http_ips2 = http_ips.copy()
            http_ips2['type'] = '代理'
            http_ips2['srcip'] = i
            http_ip_list.append(http_ips2)
    else:
        http_ip_list.append(http_ips)
    return http_ip_list


def basecode(body):
    """
    :body:请求体或响应体
    :content:对内容base64解码
    """
    body1 = ''
    if body:
        try:
            body1 = base64.b64decode(body).decode('utf-8')
        except:
            body1 = body
    return body1


def http_visit(element, account, url, urlc, app):
    """
    :param element: kafka含http数据
    :es:es连接
    :doc 空列表 批量插入 需要
    :ind :消费条数
    :begintime 开始时间
    :return:
    :content 从流量中解析数据，返回字典
    """
    http_vist = {}
    # http_vist['gmt_create'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    # http_vist['gmt_modified'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    # http_vist['creator'] = 'all'
    # http_vist['owner'] = 'all'
    http_vist['srcip'] = element.get('src_ip')
    http_vist['srcport'] = element.get('src_port')
    http_vist['dstip'] = element.get('dest_ip')
    dstport = element.get('dest_port')
    http_vist['dstport'] = dstport
    http_vist['timestamp'] = element.get('timestamp')
    http_vist['app'] = app
    http_vist['url'] = urlc  # url是处理后，url是原，写反了别忘了改
    http_vist['url_a'] = url

    content_length = element.get('http').get('length', 0)
    # if not content_length:
    #    content_length = element.get('http').get('length',0)
    # response_body = element.get('http_response_body',"")
    # request_body = element.get('http_request_body',"")
    # base64解码
    # response_bd = basecode(response_body)
    # request_bd = basecode(request_body)
    # if data_type != "XML" and data_type != "数据文件" and data_type != "JSON" and data_type != "动态脚本":
    # del element["http_response_body"]
    # del element['http_request_body']
    http_vist['content_length'] = content_length
    # http_vist['httpjson'] = json.dumps(element,ensure_ascii=False)
    http_vist['httpjson'] = ujson.dumps(element)
    http_vist['account'] = account
    return http_vist

'''
def account_search(element, parameter, request_body, loginls):
    """
    于cookies中检索关键词 ,返回account
    # loginls = ['userName', 'userid', 'account', 'loginid', 'loginname', 'email', 'phone']
    """
    cookies = element.get('http').get('cookie')
    # uri = element.get('http').get("url")
    # if uri and '?' in uri:
    #     parameter = uri.split('?')[-1]
    # else:
    #     parameter = ''
    # http_request_body = element.get('http_request_body')
    # try:
    #     http_request_body = base64.b64decode(http_request_body).decode('utf-8')
    # except:
    #     pass
    #try:
    #    request_body = parse.unquote(request_body)
    #    request_body = html.unescape(request_body)
    #except:
    #    pass
    account = ''
    account_type = ''
    if cookies:
        account, account_type = search(loginls, cookies)
    if not account_type and parameter:
        if "name" in loginls:
            loginls_par = loginls.remove("name")
        else:
            loginls_par = loginls
        account, account_type = search(loginls_par, parameter)
    if not account_type and request_body:
        account, account_type = search(loginls, request_body)
    # if not account_type and response_body:
    # account, account_type = search(loginls, response_body)
    #account = parse.unquote(account)
    return [account, account_type]


def search(login, cookie):
    acc = ''
    acc_t = ''
    for field in login:
        # modify by rzc 2023-8-31
        if field.lower() in cookie.lower():
            acc = re.findall(r'(?:\'|\")%s(?:\'|\")\s*:\s*(?:\'|\")(.*?)(?:\'|\")' % field, cookie, re.I)
            if not acc:
                acc = re.findall(r'\b%s[:=](.*?)(?:[;\n=]|$)' % field, cookie, re.I)
            if acc:
                acc = acc[0]
            else:
                acc = ''
            if acc != '':
                acc_t = field
                break
        # comment by rzc 2023-8-31
        # if re.findall(r'%s' % login[i], cookie, re.I):
        #     acc = re.findall(r'%s[:=](.*?)\W' % login[i], cookie, re.I)
        #     if not acc:
        #         acc = re.findall(r'%s[=:](.*?)$' % login[i], cookie, re.I)
        #     if not acc:
        #         acc = re.findall(r'\"%s\"[=:]\"(.*?)\"' % login[i], cookie, re.I)
        #     if not acc:
        #         acc = re.findall(r'\'%s\'[=:]\'(.*?)\'' % login[i], cookie, re.I)
        #     #if not acc:
        #         #acc = re.findall(r'%s=(.*?)' % login[i], cookie, re.I)
        #     if acc:
        #         acc = acc[0]
        #     else:
        #         acc = ''
        #     if acc != '':
        #         acc_t = login[i]
        #         break
    return acc, acc_t

'''
def account_data(timestamp, length, account, type):
    """
    :param element: kafka含http数据
    :param account_list: 去重列表
    :return:
    """
    http_account = {}
    # http_account['gmt_create'] = datetime.datetime.now()
    # http_account['gmt_modified'] = datetime.datetime.now()
    # http_account['creator'] = 'all'
    # http_account['owner'] = 'all'
    http_account['account'] = account
    http_account['flag'] = account
    http_account['type'] = type
    http_account['dept'] = ''
    http_account['firsttime'] = timestamp
    http_account['lasttime'] = timestamp
    http_account['ip_num'] = 1
    http_account['api_num'] = 1
    http_account['app_num'] = 1
    http_account['visit_num'] = 1
    http_account['visit_flow'] = length
    return http_account


def http_apps(server, timestamp, response_body, hostname, lans):
    """
    :param element: kafka含http数据
    :param app_list: 去重列表
    :lans : ['192.168', '10.', '172.16']
    :return:
    :content :从流量中解析数据，返回字典
    """
    http_app = {}
    # https = element.get('http')
    # http_app['gmt_create'] = datetime.datetime.now()
    # http_app['gmt_modified'] = datetime.datetime.now()
    # http_app['creator'] = 'all'
    # http_app['owner'] = 'all'
    http_app['app'] = hostname
    http_app['name'] = hostname
    http_app['visits_num'] = 1
    http_app['api_num'] = 1
    http_app['account_num'] = 1
    http_app['srcip_num'] = 1
    http_app['sensitive_label'] = "0"
    # bool_app = 0
    # for lan in lans:
    #     if hostname.startswith(lan):
    #         bool_app = 1
    #         break
    # if bool_app:
    #     # 1 局域网
    #     http_app['app_type'] = 1
    # elif hostname.startswith('127.0.0.1'):
    #     # 如果hostname 等于127.0.0.1   说明 用了代理模式， srcip 存在开发行为  把app赋值为dest_ip
    #     # http_app['app'] = element.get('dest_ip')
    #     http_app['app_type'] = 1
    # else:
    #     # 3.互联网
    #     http_app['app_type'] = 0

    # http_request_body = https.get('http_request_body')
    # req_label = sensite_data(http_request_body)
    # http_app['req_label'] = req_label
    # response_body = element.get('http_response_body',"")
    # try:
    #     response_body = base64.b64decode(response_body).decode('utf-8')
    # except:
    #     response_body = response_body
    # try:
    #     response_body = parse.unquote(response_body)
    # except:
    #     pass
    # res_label = sensite_data(response_body)
    # http_app['res_label'] = res_label
    http_app['server'] = server
    # http_app['first_time'] = element.get('timestamp')
    http_app['first_time'] = timestamp
    if response_body and '<title>' in response_body:
        try:
            app_title = re.findall(r'<title>(.*?)</title>', response_body)[0]
            http_app['app_title'] = app_title
        except Exception as e:
            # print('含有title的响应体', e)
            pass
    else:
        http_app['app_title'] = ''
    return http_app


def http_alerts(element):
    """
    :param :element 流量
    :content :从流量中解析alert类型数据，返回字典
    """
    http_alert = {}
    alert = element.get('alert')
    # http_alert['gmt_create'] = datetime.datetime.now()
    # http_alert['gmt_modified'] = datetime.datetime.now()
    # http_alert['creator'] = 'all'
    # http_alert['owner'] = 'all'
    http_alert['first_time'] = element.get('timestamp')
    http_alert['last_time'] = element.get('timestamp')

    http_alert['dstip'] = element.get('dest_ip')
    http_alert['dstport'] = element.get('dest_port')
    http_alert['srcip'] = element.get('src_ip')
    http_alert['srcport'] = element.get('src_port')
    http_alert['risk_label'] = alert.get('category')
    http_alert['risk_sign'] = alert.get('signature')
    http_alert['risk_level'] = alert.get('severity')
    http_alert['content'] = str(alert.get('metadata'))
    http_alert['is_verify'] = 0
    return http_alert


def monitor_data(response, re_data, data, whitelist, fid_mch_off, sen_dic, url):
    """
    :param:o:流量
    :param:account:账户 信息
    :param:url 去重接口
    :param:url_d原接口
    :param:hostname 应用
    :param:srcip:终端
    :param :parameter参数
    :risk_level：风险等级
    :api_type:接口类型
    :mname:接口名
    :app_name：应用名
    :content 从流量中解析字典返回字典
    """
    info = {}
    total_info = {}
    total_count = {}
    # senti = sentivite_identify()
    if response:
        if fid_mch_off == "true":
            # 字段识别
            sen_data, response = match_data(response, sen_dic, url)
        else:
            # 普通识别
            sen_data = filter_data(data, response, whitelist)
        # else:
        #     #sw识别 加正则规则
        #     messages, sen_data = senti.get_data(response)
        #     response = messages
        #     # add by rzc 2023/5/15 添加正则规则
        #     sen_data = re_rules(data, messages, sen_data, whitelist)
        if sen_data:
            total_info["响应体"] = {k: list(set(v)) for k, v in sen_data.items()}

            total_count["响应体"] = {k: len(list(set(v))) for k, v in sen_data.items()}
            info["响应体"] = {k: {"数量": len(list(set(v))), "内容": list(set(v))} for k, v in sen_data.items()}
    if re_data:
        if fid_mch_off == "true":
            sen_data, re_data = match_data(re_data, sen_dic, url)
            # sen_data = re_rules(data, re_data, sen_data, whitelist)
        else:
            sen_data = filter_data(data, re_data, whitelist)

        # else:
        #     messages, sen_data = senti.get_data(re_data)
        #     re_data = messages
        #     # add by rzc 2023/5/15 添加正则规则
        #     sen_data = re_rules(data, messages, sen_data, whitelist)
        if sen_data:
            total_info["请求体"] = {k: list(set(v)) for k, v in sen_data.items()}

            total_count["请求体"] = {k: len(list(set(v))) for k, v in sen_data.items()}
            info["响应体"] = {k: {"数量": len(list(set(v))), "内容": list(set(v))} for k, v in sen_data.items()}
    return response, re_data, total_info, total_count,info


def filter_data(data, message, whitelist):
    da = {}
    for re_match in data:
        # an = []
        an = re.findall(re_match["name"], message)
        # an.extend(an1)
        ##{“响应体”:{"姓名":[]}}
        if an:
            if re_match["rekey"] in whitelist:
                worng_name = whitelist.get(re_match["rekey"])
                an = list(set(an) - set(worng_name))
                if not an:
                    continue
            da[re_match["rekey"]] = an
    return da


def re_rules(rule_list, message, sen_data, whitelist):
    """
    #add by rzc 2023/5/15 添加正则规则
    :param rule_list:
    :param message:
    :param sen_data:
    :return:
    """
    # 正则匹配
    # 判断存在几个白名单信息
    # whites=list(whitelist.keys())
    for rule in rule_list:
        if rule.get("off") == 1:
            an = re.findall(rule["name"], message)
            if an:
                # 判断识别名称是否存在与白名单中 ，如果存在则取出改键值的白名单 进行剔除
                if rule["rekey"] in whitelist:
                    worng_name = whitelist.get(rule["rekey"])
                    an = list(set(an) - set(worng_name))
                    if not an:
                        continue
                if rule["rekey"] not in sen_data:
                    sen_data[rule["rekey"]] = an
                else:
                    sen_data[rule["rekey"]].extend(an)
    # else:
    #     for rule in rule_list:
    #         if rule["rekey"] =="身份证":
    #             an=re.findall(rule["name"], message)
    #             if an:
    #                 if rule["rekey"] not in sen_data:
    #                     sen_data[rule["rekey"]]=an
    #                 else:
    #                     sen_data[rule["rekey"]].extend(an)
    #         elif rule["rekey"]=="手机号":
    #             an=re.findall(rule["name"], message)
    #             if an:
    #                 if rule["rekey"] not in sen_data:
    #                     sen_data[rule["rekey"]]=an
    #                 else:
    #                     sen_data[rule["rekey"]].extend(an)
    return sen_data


# 22/06/27 lhq xiangying  yanshi  yilai  1.0.7 csr
def delay_alarm(o, url, sight, sign, severity):
    """
    :param o 流量
    :param url 原接口
    :param sight  轻微
    :param sign 重要
    :param severity 严重
    :content从流量中解析字典 判断告警标准，返回字典
    """
    deam = {}
    if not sight or not sign or not severity:
        sight = 50
        sign = 100
        severity = 150
    age = float(o.get('http').get('age', 0))
    http_method = o.get('http').get('http_method')
    timestamp = o.get('timestamp')
    timestam = o.get('timestamp')[0:-12].replace('T', ' ')
    if age:
        ag = round(age / 1000, 2)
        value = '响应{}ms'.format(ag)
        if ag > sight:
            if sight < ag <= sign:
                level = "0"
            elif sign < ag <= severity:
                level = "1"
            else:
                level = "2"
            level_js = {"0": "轻微", "1": "重要", "2": "严重"}
            content = '响应时间:{}ms;级别:{};发生时间:{}'.format(ag, level_js[level], timestam)
            deam["url"] = url
            deam["time"] = timestamp
            deam["type"] = http_method
            deam["warn_level"] = level
            deam["warn_value"] = value
            deam["content"] = content
            return deam


# 22/10/20 pjb 1.0.9.2 csr
#def real_ip(request_headers, srcip):
#    """
#    :element: kafka含http数据
#    :return:
#    :X-Real-IP 真实的IP
#    """
#    real_ip = ''
#    agent_ip = ''
#    try:
        # request_headers = element.get('http').get('request_headers')
#        for i in request_headers:
#            if i['name'] == 'X-Forwarded-For':
#                ip = i['value'].split(',')
#                ip2 = []
#                for i in ip:
#                    ip2.append(i.strip())
#                real_ip = ip2[0]
#                agent_ip = ip2[1:]
#                agent_ip.append(srcip)
#    except:
#        pass
#    return real_ip, agent_ip


# 22/11/11 pjb API19-3 8
# def api19_3(time,parameter, request_headers, request_body, response_body, data, sen_num, fc, count, aggs):
#     info = {}
#     key = {}
#     for re_match in data:
#         an = []
#         an1 = re.findall(re_match["name"], parameter)
#         an2 = re.findall(re_match["name"], request_body)
#         an3 = re.findall(re_match["name"], response_body)
#         an.extend(an1)
#         an.extend(an2)
#         an.extend(an3)
#         if len(an) != 0:
#             key[re_match["rekey"]] = len(an)
#             info[re_match["rekey"]] = []
#         if an != []:
#             info[re_match["rekey"]].extend(an)
#     type = {}
#     data = {}
#     datas = []
#     data_num = 0
#     for a in key.values():
#         data_num += a
#     type_num = 0
#     for a in info.values():
#         type_num += 1
#     # API19-3-2
#     kk = {}
#     if sen_num["API19-3-2"] <= type_num:
#         type["type"] = "API19-3-2"
#         kk["单次访问数据类型过多"] = type_num
#         kk["访问时间"] = time
#         kk["类型"] = key
#         type["more"] = kk
#         datas.append(type)
#     # API19-3-1
#     ii = {}
#     if sen_num["API19-3-1"] <= data_num:
#         data["type"] = "API19-3-1"
#         ii["单次访问数据量过大"] = data_num
#         ii["访问时间"] = time
#         ii["数据"] = info
#         data["more"] = ii
#         datas.append(data)
#
#     # API19-3-3
#     parlist = {}
#     more = {}
#     more["返回数据量可修改"] = []
#     par = sen_num["API19-3-3"].split(",")
#
#     for i in range(len(par)):
#         if re.findall(r'&%s=\d+' % par[i], parameter, re.I):
#             more["返回数据量可修改"].append('位置=参数')
#             more["返回数据量可修改"].append(parameter)
#             break
#
#     for item in request_headers:
#         for i in range(len(par)):
#             if item["name"] == par[i] and isinstance(item["value"], int):
#                 more["返回数据量可修改"].append('位置=请求头')
#                 more["返回数据量可修改"].append(request_headers)
#                 break
#         else:
#             continue
#         break
#
#     for i in range(len(par)):
#         if re.findall(r'"%s":\d+' % par[i], request_body, re.I):
#             more["返回数据量可修改"].append('位置=请求体')
#             more["返回数据量可修改"].append(request_body)
#             break
#     if more["返回数据量可修改"]:
#         more["访问时间"] = time
#         parlist["type"] = "API19-3-3"
#         parlist["more"] = more
#         datas.append(parlist)
#
#     # API19-3-4
#
#     dataf = {}
#     if count >= 100 and fc > sen_num["API19-3-4"]:
#         dataf["type"] = "API19-3-4"
#         dataf["more"] = {}
#         dataf["more"]["返回数据方差过大"] = fc
#         dataf["more"]["平均值"] = aggs/count
#         dataf["more"]["访问时间"] = time
#         datas.append(dataf)
#
#     return datas

def sen_data_count(parameter, request_body, response_body, data):
    # 敏感数据数量
    an = []
    for re_match in data:
        an1 = re.findall(re_match["name"], parameter)
        an2 = re.findall(re_match["name"], request_body)
        an3 = re.findall(re_match["name"], response_body)
        an.extend(an1)
        an.extend(an2)
        an.extend(an3)
    if len(an) != 0:
        return len(an)
    else:
        return 0


# sql接口
def api19_8(time, parameter, request_headers, request_body, sen_num, sen_num2):
    # API19-8-1,2
    datas = []
    # 详情字典
    api19_8_1 = {}
    api_1 = []
    api19_8_2 = {}
    api_2 = []
    sql1 = sen_num["API19-8-1"].split(",")
    sql2 = sen_num["API19-8-2"].split(",")

    for i in range(len(sql1)):
        if sql1[i] == 'select':
            if re.findall(r'[\W|\d]%s\W.*[\W|\d]FROM\W' % sql1[i], request_body, re.I):
                api19_8_1["type"] = "API19-8-1"
                api_1.append('位置=请求体')
                api_1.append(request_body)
                break
    for i in range(len(sql2)):
        if sql2[i] == 'delete':
            if re.findall(r'[\W|\d]%s\W.*[\W|\d]FROM\W' % sql2[i], request_body, re.I):
                api19_8_2["type"] = "API19-8-2"
                api_2.append('位置=请求体')
                api_2.append(request_body)
                break
        if sql2[i] == 'insert':
            if re.findall(r'[\W|\d]%s\W.*[\W|\d]into\W.*[\W|\d]values\W' % sql2[i], request_body, re.I):
                api19_8_2["type"] = "API19-8-2"
                api_2.append('位置=请求体')
                api_2.append(request_body)
                break
        if sql2[i] == 'update':
            if re.findall(r'[\W|\d]%s\W.*[\W|\d]set\W' % sql2[i], request_body, re.I):
                api19_8_2["type"] = "API19-8-2"
                api_2.append('位置=请求体')
                api_2.append(request_body)
                break
        if sql2[i] == 'alter':
            if re.findall(r'[\W|\d]%s\W.*[\W|\d]table\W' % sql2[i], request_body, re.I):
                api19_8_2["type"] = "API19-8-2"
                api_2.append('位置=请求体')
                api_2.append(request_body)
                break
        if sql2[i] in ["create", "drop", "truncate"]:
            if re.findall(r'[\W|\d]%s[\W|\d].*[\W|\d]table\W' % sql2[i], request_body, re.I):
                api19_8_2["type"] = "API19-8-2"
                api_2.append('位置=请求体')
                api_2.append(request_body)
                break

    for i in range(len(sql1)):
        if re.findall(r'[\W|\d]%s\W.*[\W|\d]FROM\W' % sql1[i], parameter, re.I):
            api19_8_1["type"] = "API19-8-1"
            api_1.append('位置=参数')
            api_1.append(parameter)
            break
    for i in range(len(sql2)):
        if sql2[i] == 'delete':
            if re.findall(r'[\W|\d]%s\W.*[\W|\d]FROM\W' % sql2[i], parameter, re.I):
                api19_8_2["type"] = "API19-8-2"
                api_2.append('位置=参数')
                api_2.append(parameter)
                break
        if sql2[i] == 'insert':
            if re.findall(r'[\W|\d]%s\W.*[\W|\d]into\W.*[\W|\d]values\W' % sql2[i], parameter, re.I):
                api19_8_2["type"] = "API19-8-2"
                api_2.append('位置=参数')
                api_2.append(parameter)
                break
        if sql2[i] == 'update':
            if re.findall(r'[\W|\d]%s\W.*[\W|\d]set\W' % sql2[i], parameter, re.I):
                api19_8_2["type"] = "API19-8-2"
                api_2.append('位置=参数')
                api_2.append(parameter)
                break
        if sql2[i] == 'alter':
            if re.findall(r'[\W|\d]%s\W.*[\W|\d]table\W' % sql2[i], parameter, re.I):
                api19_8_2["type"] = "API19-8-2"
                api_2.append('位置=参数')
                api_2.append(parameter)
                break
        if sql2[i] in ["create", "drop", "truncate"]:
            if re.findall(r'[\W|\d]%s\W.*[\W|\d]table\W' % sql2[i], parameter, re.I):
                api19_8_2["type"] = "API19-8-2"
                api_2.append('位置=参数')
                api_2.append(parameter)
                break

    for i in range(len(sql2)):
        if sql2[i] == 'delete':
            if re.findall(r'[\W|\d]%s\W.*[\W|\d]FROM\W' % sql2[i], str(request_headers), re.I):
                api19_8_2["type"] = "API19-8-2"
                api_2.append('位置=请求头')
                api_2.append(request_headers)
        if sql2[i] == 'insert':
            if re.findall(r'[\W|\d]%s\W.*[\W|\d]into\W.*[\W|\d]values\W' % sql2[i], str(request_headers), re.I):
                api19_8_2["type"] = "API19-8-2"
                api_2.append('位置=请求头')
                api_2.append(request_headers)
        if sql2[i] == 'update':
            if re.findall(r'[\W|\d]%s\W.*[\W|\d]set\W' % sql2[i], str(request_headers), re.I):
                api19_8_2["type"] = "API19-8-2"
                api_2.append('位置=请求头')
                api_2.append(request_headers)
        if sql2[i] == 'alter':
            if re.findall(r'[\W|\d]%s\W.*[\W|\d]table\W' % sql2[i], str(request_headers), re.I):
                api19_8_2["type"] = "API19-8-2"
                api_2.append('位置=请求头')
                api_2.append(request_headers)
        if sql2[i] in ["create", "drop", "truncate"]:
            if re.findall(r'[\W|\d]%s\W.*[\W|\d]table\W' % sql2[i], str(request_headers), re.I):
                api19_8_2["type"] = "API19-8-2"
                api_2.append('位置=请求头')
                api_2.append(request_headers)
    for i in range(len(sql1)):
        if re.findall(r'[\W|\d]%s\W.*[\W|\d]FROM\W' % sql1[i], str(request_headers), re.I):
            api19_8_1["type"] = "API19-8-1"
            api_1.append('位置=请求头')
            api_1.append(request_headers)

    if api19_8_1:
        api19_8_1["more"] = {}
        api19_8_1["more"]["SQL查询接口"] = api_1
        api19_8_1["more"]["访问时间"] = time
        datas.append(api19_8_1)
    if api19_8_2:
        api19_8_2["more"] = {}
        api19_8_2["more"]["SQL执行接口"] = api_2
        api19_8_2["more"]["访问时间"] = time
        datas.append(api19_8_2)
    # API19-3-3
    parlist = {}
    more = {}
    more["返回数据量可修改"] = []
    par = sen_num2["API19-3-3"].split(",")
    if parameter != '':
        for i in range(len(par)):
            if re.findall(r'&%s=\d+' % par[i], parameter, re.I):
                more["返回数据量可修改"].append('位置=参数')
                more["返回数据量可修改"].append(parameter)
                break
    if request_headers:
        for item in request_headers:
            for i in range(len(par)):
                if item.get("name") == par[i] and isinstance(item.get("value"), int):
                    more["返回数据量可修改"].append('位置=请求头')
                    more["返回数据量可修改"].append(request_headers)
                    break
            else:
                continue
            break
    if request_body:
        for i in range(len(par)):
            if re.findall(r'"%s":\d+' % par[i], request_body, re.I):
                more["返回数据量可修改"].append('位置=请求体')
                more["返回数据量可修改"].append(request_body)
                break
    if more["返回数据量可修改"]:
        more["访问时间"] = time
        parlist["type"] = "API19-3-3"
        parlist["more"] = more
        datas.append(parlist)
    return datas


# 公网敏感数据
def api19_7_5(src_ip, time, parameter, request_body, response_body, data):
    datas = {}
    info = {}
    key = {}
    for re_match in data:
        an = []
        an1 = re.findall(re_match["name"], response_body)
        an2 = re.findall(re_match["name"], request_body)
        an3 = re.findall(re_match["name"], parameter)
        an.extend(an1)
        an.extend(an2)
        an.extend(an3)
        if len(an) != 0:
            key[re_match["rekey"]] = len(an)
            info[re_match["rekey"]] = []
        if an != []:
            info[re_match["rekey"]].extend(an)
    if key and info:
        datas["源端IP"] = src_ip
        datas["访问时间"] = time
        datas["敏感数据类型"] = key
        datas["敏感数据"] = info
    return datas


def sensitive(element, sen, op, areas_content, err_name):
    http_request_body = ''
    req_label = ''
    parameter_label = ''
    response_body = ''
    res_label = ''
    cookie_label = ''
    parameter_labell = ''
    cookie_labell = ''
    req_labell = ''
    res_labell = ''
    url_a = element.get('url_a')
    parameter = element.get('parameter')
    uri = re.findall(r'(?:http://)(?:.*?/)(.*)', url_a)
    o = json.loads(element.get('httpjson'))
    cookie = o.get('cookie')
    if uri:
        # api为空不做判断
        # 请求数据标签 身份证,电话,账号等
        http_request_body = o.get('http_request_body')
        try:
            http_request_body = base64.b64decode(http_request_body).decode('utf-8')
        except:
            pass
        try:
            http_request_body = parse.unquote(http_request_body)
        except:
            pass
        response_body = o.get('http_response_body')
        # 返回数据标签  身份证,电话,账号等 response_body http_response_body 键对应的数据中存在
        try:
            response_body = base64.b64decode(response_body).decode('utf-8')
        except:
            response_body = response_body
        try:
            response_body = parse.unquote(response_body)
        except:
            pass
        req_label, req_labell, req_labelll = sensite_data(http_request_body, sen, op, areas_content, err_name)
        parameter_label, parameter_labell, parameter_labelll = sensite_data(parameter, sen, op, areas_content, err_name)
        res_label, res_labell, res_labelll = sensite_data(response_body, sen, op, areas_content, err_name)
        cookie_label, cookie_labell, cookie_labelll = sensite_data(cookie, sen, op, areas_content, err_name)

    def senm(k2, k3):
        s = {}
        ss = []
        for a in range(len(k2)):
            s["key"] = k2[a]
            if len(k3[a]) > 1:
                # print(k3[a])
                for i in range(len(k3[a])):
                    # 敏感类型
                    s["message"] = k3[a][i]
                    s["id"] = str(uuid.uuid1())
                    ss.append(deepcopy(s))
                    # print(ss)
            else:
                s["message"] = k3[a][0]
                s["id"] = str(uuid.uuid1())
                ss.append(deepcopy(s))
        return ss

    http_sen = {}
    senall = []
    if parameter_label or req_label or res_label or cookie_label:
        http_sen['url'] = element.get('url_a')
        http_sen['url_c'] = element.get('url')
        http_sen['time'] = element.get('timestamp')
        http_sen['request_body'] = http_request_body
        http_sen['response_body'] = response_body
        http_sen['parameter'] = parameter
        http_sen['cookie'] = cookie
        http_sen['account'] = element.get('account')
        http_sen['flow_id'] = element.get('flow_id')
        http_sen['real_ip'] = element.get('real_ip')
        http_sen['app'] = element.get('app')
        http_sen['srcip'] = element.get('srcip')
        # http_sen['app'] = hostname
        # http_sen['srcip'] = srcip
        # http_sen['account'] = account
        http_sen['sens'] = ''
        if parameter_label:
            http_sen['sens'] = '参数'
            sss = senm(parameter_labell, parameter_labelll)
            for i in sss:
                http_sen.update(i)
                senall.append(deepcopy(http_sen))
        if cookie_label:
            http_sen['sens'] = 'cookie'
            sss = senm(cookie_labell, cookie_labelll)
            for i in sss:
                http_sen.update(i)
                senall.append(deepcopy(http_sen))
        if req_label:
            http_sen['sens'] = '请求体'
            sss = senm(req_labell, req_labelll)
            for i in sss:
                http_sen.update(i)
                senall.append(deepcopy(http_sen))
        if res_label:
            http_sen['sens'] = '响应体'
            sss = senm(res_labell, res_labelll)
            for i in sss:
                http_sen.update(i)
                senall.append(deepcopy(http_sen))
    return senall
# http://100.78.1.125
