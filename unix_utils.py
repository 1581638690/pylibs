import base64
import uuid
import time
import random
import json
import socket
import ipaddress

"""base64解码"""


def base64_decode(x):
    try:
        a = base64.b64decode(x).decode("utf-8")
    except:
        try:
            a = base64.b64decode(x).decode("gbk")
        except:
            a = x
    return a


"""json字符串判断"""


def is_json_string(s):
    try:
        json.loads(s)
        return True
    except ValueError:
        return False


"""域内外判断"""


def jk_tf(json_wdgl):
    wds = []
    wd_list = json_wdgl.get("wd_table")  # 获取到网段地址
    if wd_list:
        for wd in wd_list:
            start_list = []
            end_list = []
            ip_segment = wd["wd"]
            yn = wd["yn"]
            ip_segment = ip_segment.strip(" ")
            seg_list = ip_segment.split(".")
            for seg in seg_list:
                if "-" in seg:
                    seg1 = seg.split("-")
                    start_list.append(seg1[0])
                    end_list.append(seg1[1])
                elif "*" == seg:
                    start_list.append("0")
                    end_list.append("255")
                # elif "0" == seg:
                # start_list.append("0")
                # end_list.append("255")
                else:
                    start_list.append(seg)
                    end_list.append(seg)
            if start_list != [] and end_list != []:
                start_str = ".".join(start_list)
                end_str = ".".join(end_list)
                a = {}

                try:
                    a["start_str"] = int.from_bytes(socket.inet_aton(start_str), byteorder='big')
                    a["end_str"] = int.from_bytes(socket.inet_aton(end_str), byteorder='big')
                except:
                    a["start_str"] = int(ipaddress.IPv6Address(start_str))
                    a["end_str"] = int(ipaddress.IPv6Address(end_str))
                a["yn"] = yn
                wds.append(a)
    return wds


def yn(ip, wd):
    # print(int.from_bytes(socket.inet_aton(ip), byteorder='big'))
    try:
        for w in wd:
            if w["start_str"] <= int.from_bytes(socket.inet_aton(ip), byteorder='big') <= w["end_str"] and w[
                "yn"] == "true":
                return True
            else:
                continue
                # pass
    except:
        pass


"""接口认证"""

from enum import Enum
import regex as re


class AuthType(Enum):
    BASIC = 1
    AK = 2
    SOAP = 3
    TOKEN = 4
    COOKIE = 5
    DEFAULT = 0


POSITIONS1 = {
    "parameters": 0,
    "request_headers": 1,
    "request_bodys": 2,
    "url": 3
}


def auths(auth_data, hostname, parameter, request_headers, http_request_body, url_c):
    auth_type = 0
    app = hostname
    for data in auth_data:
        app_list = data.get('app', "").split("|")
        if app in app_list and data.get("off") == "true":
            # 进行识别
            params, method, pos, rule, value = data.get("params"), data.get("auth_method"), data.get(
                "pos"), data.get("params"), data.get("params_arg")

            auth_type = re_match(method, pos, rule, value, parameter, request_headers, http_request_body, url_c)
    return auth_type


def re_match(method, pos, rule, value, *args):
    au = con(pos, rule, value, *args)
    if au:
        return AuthType[method.upper()].value  # 返回识别到的认证索引
    return AuthType.DEFAULT.value  # 返回默认索引


def con(pos, rule, value, *args):
    """
    根据自定义规则进行识别
    :param pos:
    :param rule:
    :param value:
    :param args:
    :return:
    """
    position_index = POSITIONS1.get(pos)
    if position_index is not None and args[position_index] != "":
        data_to_check = args[position_index]
        if pos in ("request_bodys", "url", "parameters") and rule != "":
            # 识别参数
            rule = '(?:^|&)(?:' + rule + ')=([^&]*)'
            par_match = re.findall(rule, data_to_check)
            condition = bool(par_match and par_match[0])
            if not value:
                return condition
            else:  # 存在关键值，但是要判断是否存在识别的值
                if condition and value in par_match[0]:
                    return True

        elif pos == "request_headers" and rule != "":
            # 识别请求头，请求头包含很多认证方式，因此存在rule与value值，需要先判断出请求头中是否包含rule值信息
            authorization_header = next(
                (header for header in data_to_check if header["name"] == rule),
                None)
            if authorization_header:
                if not value:  # 如果值不存在，表示仅仅只做键的识别，直接返回True
                    return True
                else:
                    # value值存在
                    # ruled = value + '\s+(\w+)'
                    # req_h = re.findall(ruled, authorization_header["value"])
                    # if value in authorization_header["value"]:
                    return bool(value in authorization_header["value"])
            else:
                return False

    return False


def ats(status, token_rule, ak_rule, parameter, http_request_body, request_headers, url_c, auth_data,
        hostname):
    """
    根据判断判断是否进行自定义识别还是普通识别
    :param status:
    :param token_rule:
    :param ak_rule:
    :param parameter:
    :param http_request_body:
    :param request_headers:
    :param url_c:
    :param auth_data:
    :param hostname:
    :return:
    """
    auth_type = AuthType.DEFAULT.value
    if status.startswith("2"):
        if auth_data and any(hostname in data.get("app", "").split("|") for data in auth_data):

            auth_type = auths(auth_data, hostname, parameter, request_headers, http_request_body, url_c)
        else:
            auth_type = ordinary_rule(token_rule, ak_rule, parameter, http_request_body, request_headers, url_c,
                                      auth_type)

    return auth_type


def ordinary_rule(token_rule, ak_rule, parameter, http_request_body, request_headers, url_c, auth_type):
    """
    普通识别
    :param token_rule:
    :param ak_rule:
    :param parameter:
    :param http_request_body:
    :param request_headers:
    :param url_c:
    :param auth_type:
    :return:
    """
    have_auth = 0
    token_rule = '(?:^|&)(?:' + token_rule + ')=([^&]*)'  # id_token/access_token/token
    ak_rule = '(?:^|&)(?:' + ak_rule + ')=([^&]*)'  # access_key/access_key_id/sign/signature
    basic_rule = "(?<=https://)([\w\W]*:[\w\W]*)(?=@)"
    soap_rule = "<(soap|soapenv):Envelope[\w\W]*<(soap|soapenv):Body"

    # token认证
    if parameter and token_auth_check(parameter, token_rule):
        have_auth, auth_type = 1, AuthType.TOKEN.value
    # 签名认证
    if not have_auth and parameter:
        ak_match = re.findall(ak_rule, parameter)
        if ak_match and ak_match[0]:
            have_auth, auth_type = 1, AuthType.AK.value
    # token认证
    if not have_auth and http_request_body and token_auth_check(http_request_body, token_rule):
        have_auth, auth_type = 1, AuthType.TOKEN.value
    # soap认证
    # if not have_auth and http_request_body and re.findall(soap_rule, http_request_body):
    # have_auth, auth_type = 1, AuthType.SOAP.value
    # basic认证
    if not have_auth and request_headers:
        # 解析request_headers中的内容并判断是否含有basic认证
        auth_type, have_auth = extract_token(request_headers, auth_type, have_auth)
    # basic认证
    # if not have_auth and re.findall(basic_rule, url_c):
    # have_auth, auth_type = 1, AuthType.BASIC.value
    return auth_type


def token_auth_check(data, token_rule):
    token_match = re.findall(token_rule, data)
    return token_match and token_match[0] != ""


def extract_token(headers, auth_type, have_auth):
    au_lst = {"Authorization", "authorization"}
    co_lst = {"Cookie", "cookie"}
    # 寻找 Authorization 头部
    authorization_header = next(
        (header for header in headers if header["name"] in au_lst), None)
    cookie_header = next((header for header in headers if header["name"] in co_lst),
                         None)
    if authorization_header and not have_auth:
        # 如果 Authorization 头部存在，检查是否包含 Token
        auth_value = authorization_header.get("value", "")
        # 尝试匹配 Bearer Token
        # token_match = re.search(r'Bearer\s+(\w+)', auth_value)

        if any(keyword in auth_value for keyword in ["bearer", "Bearer", "token"]):
            have_auth, auth_type = 1, AuthType.TOKEN.value

        # 尝试匹配 Basic 认证中的 Token
        if have_auth != 1:
            # basic_match = re.search(r'Basic\s+(\w+)', auth_value)
            # if 'basic' in auth_value or "Basic" in auth_value:
            if any(keyword in auth_value for keyword in ["basic", "Basic"]):
                have_auth, auth_type = 1, AuthType.BASIC.value
    if cookie_header and not have_auth:
        cookie_value = cookie_header.get("value", "")
        if cookie_value:
            have_auth, auth_type = 1, AuthType.COOKIE.value
    return auth_type, have_auth


"""资源文件判断"""


def type_class(content_type, ht_type, uri, parameter):
    data_type = "未知"
    # Delete 注释 by rzc on 2023-04-10 14:52:55
    c_k_list, c_v_list = zip(*content_type.items())
    kvalue = next((k for k, v in content_type.items() if v == "动态脚本"), None)
    kv_s = kvalue.split("/")
    if parameter:
        if "html" in ht_type:
            data_type = "动态脚本"
    splits = uri.split("/")
    if data_type != "动态脚本":
        if ht_type:
            data_type = next(
                (c_v_list[i] for i in range(len(content_type)) if c_k_list[i] in ht_type or c_k_list[i] == ht_type),
                "未知")
        else:
            data_type = "未知"
    if splits[-1].endswith("."):
        if len(splits) >= 2:
            find = splits[-1].split(".")
            if find and find[-1] in kv_s:
                data_type = "动态脚本"
    counts = len(splits)
    return data_type, counts


"""接口类型判断"""


def api_types(http, data_type, logoutls, http_url):
    https = http.get('http', '')
    url = https.get('url')

    # 请求方式
    method = https.get('http_method', '')
    request_headers = https.get('request_headers', '')
    response_headers = https.get('response_headers', '')
    request_body = http.get('http_request_body', '')
    response_body = http.get('http_response_body', '')

    # -----开始判断----
    # 0-其他 1-登陆 3-上传 4-下载 5-服务 8-注销
    api_type = 0
    # 判断请求是否是POST
    if method == "POST":
        # 判断是否是上传接口
        # 判断Content-Type中是否含有‘multipart/form-data’和‘binary/octet-stream’
        header_ok = 0
        for header in request_headers:
            #if header.get('name', '') == 'content-type' or header.get('name', '') == "Content-Type":
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
        for i in ["成功", "success", "失败", "错误", "fail", 'true', 'error', 'suc', '"code": 200', '"code": 1',
                  '"code": 400',
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
                for i in ["session", "token", "auth", "appid", "deviceid", "ticket", "client_key", "lid",
                          "grafana_remember", "sessid", "grafana_sess", "clientid"]:
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
    return api_type

"""账户识别优化版"""

"""真实IP提取"""


def real_ip(request_headers, srcip):
    """
    :element: kafka含http数据
    :return:
    :X-Real-IP 真实的IP
    """
    real_ip = ''
    agent_ip = []
    # try:
    #     # request_headers = element.get('http').get('request_headers')
    #     for i in request_headers:
    #         if i['name'] == 'X-Forwarded-For':
    #             ip = i['value'].split(',')
    #             ip2 = []
    #             for i in ip:
    #                 ip2.append(i.strip())
    #             real_ip = ip2[0]
    #             agent_ip = ip2[1:]
    #             agent_ip.append(srcip)
    # except:
    #     pass
    try:
        # 遍历请求头，查找”X-Forwarded-For“
        for header in request_headers:
            if header["name"] == 'X-Forwarded-For':
                ips = [ip.strip() for ip in header["value"].split(",")]
                real_ip = ips[0]
                agent_ip = ips[1:]
                agent_ip.append(srcip)
                break
    except (KeyError, AttributeError) as e:
        pass
    return real_ip, agent_ip
