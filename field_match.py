# -*- coding:utf-8 -*-
# @FileName  :Raway_custom.py
# @Time      :2023-07-12 15:08
# @Author    :Rzc
""""""
"""
需求：根据客户数据进行定制，因敏感识别误报信息，所以考虑进行字段匹配,考虑进行不同应用下对不同的字段进行分类判断识别字段
开发：设计成前台可配置界面，目前包含两个参数:字段名称,分类名称（例：字段名称 name,分类名称 姓名；）
局限性：会出现重复性字段且字段内容不同,导致字段内容与分类名称不符，无法根据某个应用去判断字段信息不同
"""
import regex as re


def get_data(data):
    """
    对数据进行合并匹配,每搁一段时间进行更新 ，这一段写到xink里面
    '"Kpfnsrsbh"\s*:\s*"([^"]*)"'
    {
        api:{type:"",
            字段：{
                    正则:"地址"
                }
            }
        }
    }
    :return:
    """
    sen_dic = {}
    if data:
        for item in data:
            api = item["api"]
            type = item["type"]
            name_list = item["name"].split("|")
            class_name_list = item["class_name"].split("|")
            off = item["off"]
            if off == "true":
                if type == "JSON" and api != "*":
                    re_str_list = ['"' + name + '"\s*:\s*"([^"]*)"' for name in name_list]
                elif type == "XML":
                    re_str_list = ['\W' + name + '\s*=\s*"([^"]*)"' for name in
                                   name_list]  # homeaddress\s*=\s*"([^"]*)"
                elif type == "JSON" and api == "*":
                    re_str_list = ['"*\\b' + name + '"*\s*[:=]\s*"([^"]*)"' for name in name_list]
                if api not in sen_dic:
                    sen_dic[api] = {}
                # sen_dic["type"]=type
                # 拼接正则表达式
                # re_str='"'+item["name"]+'"\s*:\s*"([^"]*)"'
                for ds in zip(name_list, class_name_list, re_str_list):
                    name = ds[0]
                    class_name = ds[1]
                    re_str = ds[2]
                    if name not in sen_dic[api]:
                        sen_dic[api][name] = {}
                        sen_dic[api][name][re_str] = class_name
                        if type == "JSON" and "json" not in sen_dic[api]:
                            sen_dic[api][name]["json"] = type
                        elif type == "XML" and "xml" not in sen_dic[api]:
                            sen_dic[api][name]["xml"] = type
                # sen_dic[api][name][re_str]=class_name
    return sen_dic


def match_data(message, sen_dic, url):
    """
    url: 传来接口与字典中的url进行判断
    优先级: sw 字段匹配优先级：url, con_url,*(精准，通用，全局)
    :param message: #请求体响应体
    :param sen_dic: #敏感正则配置
    :return:
    """
    sen_data = {}
    new_message = message
    local_values = False

    if url in sen_dic:  # 这个为最首要条件
        # 如精准接口存在与字典中
        data = sen_dic.get(url)
        sen_data, new_message = redata_match(data, message, sen_data)

    else:  # 无相同接口，对其进行模糊搜索匹配
        # 对模糊接口进行测试
        for api, data in sen_dic.items():
            # 进行正则分析,拿着api与流里面的url进行的对比
            if url.startswith(api):
                local_values = True
                sen_data, new_message = redata_match(data, message, sen_data)

        if local_values == False:  # 为全局*的正则匹配
            url = "*"
            data = sen_dic.get(url)
            sen_data, new_message = redata_match(data, message, sen_data)
    # 判断sen_data是否为空 为空则表示没有匹配到数据
    return sen_data, new_message


def redata_match(data, message, sen_data):
    """
    name:kpfnsrsbh
    strs:正则表达  "*kpfnsrsbh*\\s*[:=]\\s*"([^"]*)"
    field:中文名
    :param data:
    :param message:
    :param sen_data:
    :return:
    """
    for name, res in data.items():
        # 只存在一个键值对，转化为迭代器
        strs, field = next(iter(res.items()))  # 第一次 是取出第一个，第二次是取出第二个键值对
        if "xml" in res and name == "col":
            col_re = r'<col\b(?:(?!linkvalue)[^>])*?\btext="([^"]*)"[^>]*\blinkvalue="[^"]*"[^>]*>(?:[^<]*)(<!\[CDATA\[(.*?)\]\]>)(?:[^<]*)?</col>'
            an_text = re.findall(col_re, message)
            for an in an_text:
                key = an[0]
                value = an[2]
                if key not in sen_data:
                    if value.startswith("<a "):  # 存在<a的标签数据
                        value_re = '>(.*?)<'
                        values = re.findall(value_re, value)
                        if values:
                            sen_data[key] = values
                    else:  # 直接存储数据
                        sen_data[key] = []
                        sen_data[key].append(value)

                else:
                    if value.startswith("<a "):  # 存在<a的标签数据
                        value_re = '>(.*?)<'
                        values = re.findall(value_re, value)
                        if values:
                            sen_data[key].extend(values)
                    else:  # 直接存储数据
                        sen_data[key].append(value)
        else:
            # strs=strs.replace("\\\\","\\")
            an_find = re.findall(strs, message, re.I)
            an = [val for val in an_find if len(val) >= 2 and val != "Null" and val != "\","]
            if an:
                message = message.replace(name, field)
                if field not in sen_data:
                    sen_data[field] = list(set(an))
                else:
                    sen_data[field].extend(an)
                    sen_data[field] = list(set(sen_data[field]))
            else:
                message = message
    return sen_data, message


if __name__ == '__main__':
    """
    1.打开铁路局按钮开关，关闭税务按钮，让铁路局跟正则识别打开
    2.需要修改审计信息
    """
    abc = {
        "createTime": "2023-03-23 12:57:16.000",
        "createUser": "1517432862573772802",
        "updateTime": "2023-05-16 15:07:52.000",
        "updateUser": "1265476890672672808",
        "id": "1531581315168018433",
        "personelIdentifier": "197161",
        "personnelOrderOrg": "1513783799982764034",
        "personnelOrderDept": "1519226791761756161",
        "personnelOrderTeam": "",
        "actualOrg": "1513783799982764034",
        "actualDept": "1519226791761756161",
        "actualTeam": "",
        "name": "卓红",
        "phone": "13592676519",
        "pinyinName": "[[zhuoweihong], [zhuoweigong]]",
        "formerName": "",
        "photoId": "1564516112882098177",
        "sex": "male",
        "nation": "01",
        "politicalStatus": "01",
        "joinTime": "1993-12-09 00:00:00.000",
        "workPermitNumber": "2066146032695",
        "identityNumber": "410802196609041516",
        "birthday": "1965-12-09 00:00:00.000",
        "hometown": "河南省濮阳市华龙区",
        "birthplace": "河南省濮阳市华龙区",
        "hkLocation": "河南省郑州市二七区勤劳街2号院4号楼48号",
        "curHomeAddress": "河南省郑州市中原区伏牛路3号院3号楼38号",
        "enlistedTime": "",
        "firstWorkTime": "1985-12-03 00:00:00.000",
        "railwayWorkTime": "1985-12-03 00:00:00.000",
        "curOrgWorkTime": "2020-11-01 00:00:00.000",
        "workAgeRegulateValue": "",
        "providentFundNumber": "014205",
        "healthInsuranceNumber": "00025033",
        "socialSecurityNumber": "",
        "healthCondition": "health_condition_01",
        "marriageStatus": "20",
        "education": "51",
        "postCode": "1010220",
        "postClassification": "04",
        "curPostTime": "2020-11-01 00:00:00.000",
        "adminLevel": "0601",
        "proTechPost": "",
        "proTechQualifications": "",
        "skillLevel": "",
        "skillLevelQualifications": "",
        "post": "",
        "adminGivenPost": "",
        "jobCategory": "0101",
        "isManageEngage": 1,
        "isClomnProdEngage": "",
        "isTeamLeader": "",
        "curWorkType": "",
        "postName": "",
        "highSpeedRailFlag": 0,
        "operationSkillPersonType": "",
        "mainPostType": "",
        "manageFlag": "management_id",
        "employmentType": "01",
        "staffClassification": "0102",
        "disabilityCertificateLevel": "11",
        "staffSource": "03",
        "partJobCategory": "",
        "partJobSubCategory": "",
        "ownedProdGroup": "",
        "workSchedule": "21",
        "isDeduceEmp": False,
        "isDeleted": False,
        "changedIndex": "",
        "isExistStaff": "",
        "specialSign": ""
    }
    import json

    abc = json.dumps(abc, ensure_ascii=False)
    import json

    data = [
        {
            "name": "hkLocation|name|phone|hometown|birthplace|curHomeAddress|identityNumber",
            "class_name": "地址|姓名|手机号|地区|地区|地址|身份证号",
            "api": "http://10.96.5.31:8081/api/hrmsOrgBasicInfo/list",
            "type": "JSON"
        },
        {
            "name": "hkLocation",
            "class_name": "详细地址",
            "api": "http://10.96.5.32:8081",
            "type": "JSON"
        },
        {
            "api": "http://10.101.60.66:8001/LumsSoapWs",
            "type": "XML",
            "name": "address|personname|homeaddress",
            "class_name": "地址|姓名|家庭住址"
        },
        {
            "api": "http://10.96.5.31:8082",
            "type": "XML",
            "name": "graduateschool|homeaddress|personname|address|handphone",
            "class_name": "学校&母校|地址|姓名|地址|手机号"
        },
        {
            "api": "http://10.96.5.31:8082/api/hrmsOrgBasicInfo/list",
            "type": "XML",
            "name": "graduateschool|homeaddress|personname|address|handphone",
            "class_name": "学母|地址1|姓名1|地址1|手机号1"
        },
        {
            "api": "*",
            "type": "",
            "name": "kpfnsrsbh|Xsfmc|gmfmc|Gmfmc|Xfmc|Gfmc|Xsfnsrsbh|Gmfnsrsbh|Lzfpdm|Lzfphm|xsfmc|gmfnsrsbh|xsfnsrsbh|xfNsryhzh|fphm|fpdm|nsrmc|nsrsbh|Gfsbh|xfsbh|xsfsbh|gmfsbh|Dqnsrsbh|xhfdz|NSRSBH|NSRMC",
            "class_name": "开票方纳税人识别号|销售方名称|购买方名称|购买方名称|销售方名称|购买方名称|销售方纳税人识别号|购买方纳税人识别号|发票代码|发票号码|销售方名称|购买方纳税人识别号|销售方纳税人识别号|销售方纳税人银行账号|发票号码|发票代码|纳税人名称|纳税人识别号|购买方识别号|销售方识别号|销售方识别号|购买方识别号|地区纳税人识别号|销货方地址|纳税人识别号|纳税人名称"
        }
    ]
    # sen_dic=get_data(data)
    # print(sen_dic)
    # urllist=["http://10.96.5.31:8081/api/hrmsOrgBasicInfo/list","http://10.101.60.66:8001/LumsSoapWs"]
    data1 = [
        {
            "name": "hkLocation|name|phone|hometown|birthplace|curHomeAddress|identityNumber",
            "class_name": "地址|姓名|手机号|地区|地区|地址|身份证号",
            "api": "http://10.96.5.31:8081/api/hrmsOrgBasicInfo/list",
            "type": "JSON"
        },
        {
            "api": "http://10.101.60.66:8001/LumsSoapWs",
            "type": "XML",
            "name": "address|personname",
            "class_name": "地址|姓名"
        },
        {
            "api": "http://150.15.134.53",
            "type": "JSON",
            "name": "xsfsbh|fphm",
            "class_name": "纳税人识别号|发票号码"
        },
        {
            "api": "http://100.78.76.36/",
            "type": "JSON",
            "name": "Xsfnsrsbh|Gmfnsrsbh|Kpfnsrsbh|Xsfmc|Gmfmc|Gfsbh",
            "class_name": "销售方识别号|购买识别号|开票方识别号|销售方名称|购买方名称|购买方识别号1"
        },
        {
            "api": "http://100.60.123.123",
            "type": "XML",
            "name": "col",
            "class_name": "无"
        }
    ]
    request_body = """<?xml version="1.0" encoding="UTF-8"?>
<table isPageAutoWrap="0" instanceid="workflowRequestListTable" tabletype="checkbox" pagesize="20" isFromFromMode="true" modeCustomid="41" page="true" recordCount="3" pagenum="1" nowpage="1" orderValue="__random__9959A753285BDEDA828F6D8B144BA517" countColumns="" orderType="DESC">
    <head>
        <col width="3%" key="true" text="&lt;input name=_allselectcheckbox type=checkbox onClick=checkAllChkBox(this.checked)&gt;" type="checkbox" />
        <col width="8%" text="姓名" column="LASTNAME" otherpara="column:ID+7502+1+1+7+1+varchar2(60)+2+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="901" />
        <col width="24%" text="所在部门" column="DEPARTMENTID" otherpara="column:ID+7507+3+4+7+1+integer+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="906" />
        <col width="20%" text="岗位" column="JOBTITLE" otherpara="column:ID+7506+3+24+7+1+integer+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="905" />
        <col width="14%" text="所在公司" column="SUBCOMPANYID1" otherpara="column:ID+7508+3+164+7+1+int+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="907" />
        <col width="13%" text="手机" column="MOBILE" otherpara="column:ID+7504+1+1+7+1+varchar2(60)+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="903" />
        <col width="14%" text="办公电话" column="TELEPHONE" otherpara="column:ID+7503+1+1+7+1+varchar2(60)+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="902" />
        <col width="5%" text="邮件地址" column="EMAIL" otherpara="column:ID+7505+1+1+7+1+varchar2(60)+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="904" />
    </head>
    <row rowClick="">
        <col text="" type="checkbox" linkvalue="1322" />
        <col width="8%" text="姓名" column="LASTNAME" otherpara="column:ID+7502+1+1+7+1+varchar2(60)+2+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="901" linkvalue="王侃" value="王侃">
            <![CDATA[<a title='王侃' =javascript:modeopenFullWindowHaveBar("/hrm/HrmTab.jsp?_fromURL=HrmResource&id=1322","1322")>王侃</a>]]>
        </col>
        <col width="24%" text="所在部门" column="DEPARTMENTID" otherpara="column:ID+7507+3+4+7+1+integer+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="906" linkvalue="440" value="440">
            <![CDATA[<a ="/hrm/company/HrmDepartmentDsp.jsp?id=440" target="_new">中铁联集宁波分公司领导</a>&nbsp;]]>
        </col>
        <col width="20%" text="岗位" column="JOBTITLE" otherpara="column:ID+7506+3+24+7+1+integer+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="905" linkvalue="920" value="920">
            <![CDATA[<a ="/hrm/jobtitles/HrmJobTitlesEdit.jsp?id=920" target="_new">中铁联集宁波分公司总经理</a>&nbsp;]]>
        </col>
        <col width="14%" text="所在公司" column="SUBCOMPANYID1" otherpara="column:ID+7508+3+164+7+1+int+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="907" linkvalue="191" value="191">
            <![CDATA[<a ="/hrm/company/HrmSubCompanyDsp.jsp?id=191" target="_new">中铁联集宁波子公司</a>&nbsp;]]>
        </col>
        <col width="13%" text="手机" column="MOBILE" otherpara="column:ID+7504+1+1+7+1+varchar2(60)+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="903" linkvalue="13616780584" value="13616780584">
            <![CDATA[13616780584]]>
        </col>
        <col width="14%" text="办公电话" column="TELEPHONE" otherpara="column:ID+7503+1+1+7+1+varchar2(60)+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="902" linkvalue="0574-27699388" value="0574-27699388">
            <![CDATA[0574-27699388]]>
        </col>
        <col width="5%" text="邮件地址" column="EMAIL" otherpara="column:ID+7505+1+1+7+1+varchar2(60)+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="904" linkvalue="" value="" />
    </row>
    <row rowClick="">
        <col text="" type="checkbox" linkvalue="1323" />
        <col width="8%" text="姓名" column="LASTNAME" otherpara="column:ID+7502+1+1+7+1+varchar2(60)+2+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="901" linkvalue="陈永华" value="陈永华">
            <![CDATA[<a title='陈永华' =javascript:modeopenFullWindowHaveBar("/hrm/HrmTab.jsp?_fromURL=HrmResource&id=1323","1323")>陈永华</a>]]>
        </col>
        <col width="24%" text="所在部门" column="DEPARTMENTID" otherpara="column:ID+7507+3+4+7+1+integer+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="906" linkvalue="440" value="440">
            <![CDATA[<a ="/hrm/company/HrmDepartmentDsp.jsp?id=440" target="_new">中铁联集宁波分公司领导</a>&nbsp;]]>
        </col>
        <col width="20%" text="岗位" column="JOBTITLE" otherpara="column:ID+7506+3+24+7+1+integer+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="905" linkvalue="921" value="921">
            <![CDATA[<a ="/hrm/jobtitles/HrmJobTitlesEdit.jsp?id=921" target="_new">中铁联集宁波分公司副总经理</a>&nbsp;]]>
        </col>
        <col width="14%" text="所在公司" column="SUBCOMPANYID1" otherpara="column:ID+7508+3+164+7+1+int+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="907" linkvalue="191" value="191">
            <![CDATA[<a ="/hrm/company/HrmSubCompanyDsp.jsp?id=191" target="_new">中铁联集宁波子公司</a>&nbsp;]]>
        </col>
        <col width="13%" text="手机" column="MOBILE" otherpara="column:ID+7504+1+1+7+1+varchar2(60)+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="903" linkvalue="18958283317" value="18958283317">
            <![CDATA[18958283317]]>
        </col>
        <col width="14%" text="办公电话" column="TELEPHONE" otherpara="column:ID+7503+1+1+7+1+varchar2(60)+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="902" linkvalue="0574-27686823" value="0574-27686823">
            <![CDATA[0574-27686823]]>
        </col>
        <col width="5%" text="邮件地址" column="EMAIL" otherpara="column:ID+7505+1+1+7+1+varchar2(60)+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="904" linkvalue="" value="" />
    </row>
    <row rowClick="">
        <col text="" type="checkbox" linkvalue="1324" />
        <col width="8%" text="姓名" column="LASTNAME" otherpara="column:ID+7502+1+1+7+1+varchar2(60)+2+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="901" linkvalue="史礼阳" value="史礼阳">
            <![CDATA[<a title='史礼阳' =javascript:modeopenFullWindowHaveBar("/hrm/HrmTab.jsp?_fromURL=HrmResource&id=1324","1324")>史礼阳</a>]]>
        </col>
        <col width="24%" text="所在部门" column="DEPARTMENTID" otherpara="column:ID+7507+3+4+7+1+integer+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="906" linkvalue="440" value="440">
            <![CDATA[<a ="/hrm/company/HrmDepartmentDsp.jsp?id=440" target="_new">中铁联集宁波分公司领导</a>&nbsp;]]>
        </col>
        <col width="20%" text="岗位" column="JOBTITLE" otherpara="column:ID+7506+3+24+7+1+integer+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="905" linkvalue="922" value="922">
            <![CDATA[<a ="/hrm/jobtitles/HrmJobTitlesEdit.jsp?id=922" target="_new">中铁联集宁波分公司财务总监</a>&nbsp;]]>
        </col>
        <col width="14%" text="所在公司" column="SUBCOMPANYID1" otherpara="column:ID+7508+3+164+7+1+int+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="907" linkvalue="191" value="191">
            <![CDATA[<a ="/hrm/company/HrmSubCompanyDsp.jsp?id=191" target="_new">中铁联集宁波子公司</a>&nbsp;]]>
        </col>
        <col width="13%" text="手机" column="MOBILE" otherpara="column:ID+7504+1+1+7+1+varchar2(60)+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="903" linkvalue="13858368316" value="13858368316">
            <![CDATA[13858368316]]>
        </col>
        <col width="14%" text="办公电话" column="TELEPHONE" otherpara="column:ID+7503+1+1+7+1+varchar2(60)+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="902" linkvalue="0574-27687717" value="0574-27687717">
            <![CDATA[0574-27687717]]>
        </col>
        <col width="5%" text="邮件地址" column="EMAIL" otherpara="column:ID+7505+1+1+7+1+varchar2(60)+0+42+-43+0+0+0+41+fromsearchlist+0+671+0" transmethod="weaver.formmode.search.FormModeTransMethod.getOthers" systemid="904" linkvalue="" value="" />
    </row>
</table>
"""
    # url="http://100.78.76.36/ebus/00000000000_nw_dzfpfwpt/yp/{p1}/v1/{p2}"
    abc2 = """03" Xsfmc="郑州铁路职业技术学院" gmfmc="高级工" maritalstatus="0" zip="450000" Dqnsrsbh="河南省郑州市管城回族区鑫苑城6号院1号楼2单元1502" inworktime="2016-08-18T00:00:00+08:00" sex="0" workplaceName="客运车间" dutyGroupIndex="0"/><return driverid="753823642" section="F31" workno="3001510" NSRMC="朱亚峰" homephone="15138902283" handphone="13298367897" postname="司机" workplace="3002" address="郑州三北小区铁道东风花园2号楼1单元2003" chedui="北线车队" education="7" idcardnum="410103197712121314" nation="汉" workcardnum="2066200015101" gmfmc="宝鸡铁路司机学校" techlevel="三级" maritalstatus="1" zip="450000" homeaddress="郑州市政通路25号楼2单元西户" sex="0" workplaceName="客运车间" dutyGroupIndex="0"></return><return driverid="753823643" section="F31" workno="3014613" personname="张永亮" handphone="15038365295" postname="副司机" workplace="3002" address="郑州市二七区苗圃单身宿舍305" chedui="北线车队" zhidaozu="第二指导组" education="4" birthdate="1995-03-29T00:00:00+08:00" idcardnum="410225199503293753" nation="汉" workcardnum="2066200146137" graduateschool="兰州交通大学博文学院" graduatenum="135141202005000992" maritalstatus="0" zip="450000" homeaddress="河南省商丘市睢阳区古宋街道和谐景苑2单元501" inworktime="2020-09-11T00:00:00+08:00" sex="0" workplaceName="客运车间" dutyGroupIndex="0"></return><return driverid="753823644" section="F31" workno="3002065" personname="赵志锋" handphone="13838336021" postname="司机" workplace="3002" address="郑州市经开区腾达路幸福滨水家园南院" chedui="北线车队" zhidaozu="第五指导组" education="4" birthdate="1974-09-27T00:00:00+08:00" idcardnum="410103197411101950" nation="汉" workcardnum="2066200020653-1" graduateschool="郑州铁路职业技术学院" graduatenum="392" techlevel="一级" maritalstatus="1" zip="450000" homeaddress="郑州市陇海东路325号恒业小区1号楼" inworktime="1993-08-01T00:00:00+08:00" sex="0" workplaceName="客运车间" dutyGroupIndex="0"></return><return driverid="753823646" section="F31" workno="3001693" personname="邓军" handphone="13653821721" postname="指导司机" workplace="3007" address="郑州市二七区碧云路冯庄小区" chedui="西线车队" education="7" idcardnum="410103197903121018" nation="汉族" graduateschool="宝鸡铁路司机学校" techlevel="高级工" maritalstatus="1" sex="0" workplaceName="调度中心" dutyGroupIndex="0"></return><return driverid="753823665" section="F31" workno="3009078" personname="张志鹏" handphone="13633817963" postname="指导司机" workplace="3007" chedui="西线车队" zhidaozu="第四指导组" education="0" maritalstatus="0" sex="0" workplaceName="调度中心" dutyGroupIndex="0"></return><return driverid="753823710" section="F31" workno="3014134" personname="王默涵" handphone="15237090988" postname="司机" workplace="3002" address="郑州市二七区正商城泰院2号院" chedui="北线车队" zhidaozu="第三指导组" education="7" birthdate="1997-06-23T00:00:00+08:00" idcardnum="411421199706230038" nation="汉" workcardnum="2066200141343" graduateschool="郑州铁路职业技术学院" techlevel="三级" maritalstatus="0" homeaddress="郑州市金水区沙口路瑞隆城一号楼63号" inworktime="2019-10-10T00:00:00+08:00" sex="0" workplaceName="客运车间" dutyGroupIndex="0"></return><return driverid="753823711" section="F31" workno="3013682" personname="闫萌萌" handphone="15225092453" postname="司机" workplace="3002" address="二七区行云路芙蓉花苑一期8-1-1702" chedui="北线车队" zhidaozu="第四指导组" education="4" birthdate="1994-11-06T00:00:00+08:00" idcardnum="410426199411061530" nation="汉" workcardnum="2066200136822" graduateschool="郑州铁路职业技术学院" graduatenum="106137202005018000" techlevel="三级" maritalstatus="1" homeaddress="郑州市管城区石化路中铁七局小区" sex="0" workplaceName="客运车间" dutyGroupIndex="0"></return><return driverid="753823722" section="F31" workno="3008570" personname="彭冲奇" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823723" section="F31" workno="3009052" personname="张旭东" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823724" section="F31" workno="3009206" personname="张祥" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823725" section="F31" workno="3008875" personname="许海澎" postname="副司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823726" section="F31" workno="3008490" personname="卢尊奡" postname="副司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823727" section="F31" workno="3009251" personname="崔珉" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823728" section="F31" workno="3009227" personname="王丰" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823729" section="F31" workno="3002340" personname="栾子卓" postname="副司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823731" section="F31" workno="3008724" personname="王海成" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823734" section="F31" workno="3009425" personname="徐军委" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823735" section="F31" workno="3009060" personname="张勇" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823737" section="F31" workno="3008819" personname="魏铁燕" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823738" section="F31" workno="3008312" personname="李丹" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823742" section="F31" workno="3008659" personname="孙全根" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823743" section="F31" workno="3009081" personname="张中华" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823745" section="F31" workno="3012093" personname="刘卓" postname="助理工程师" workplace="3010" education="0" maritalstatus="0" sex="0" workplaceName="运用科" dutyGroupIndex="0"></return><return driverid="753823746" section="F31" workno="3010013" personname="蔡建云" postname="学员" workplace="3016" education="0" maritalstatus="0" sex="0" workplaceName="南整备车间" dutyGroupIndex="0"></return><return driverid="753823749" section="F31" workno="3008696" personname="王朝" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823762" section="F31" workno="3012437" personname="张亮" postname="副司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823763" section="F31" workno="3011986" personname="刘少东" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823767" section="F31" workno="3009264" personname="候红斌" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823783" section="F31" workno="3001850" personname="陈松涛" postname="分析员" workplace="3005" chedui="车间" education="0" maritalstatus="0" sex="0" workplaceName="调小运用车间" dutyGroupIndex="0"></return><return driverid="753823784" section="F31" workno="3002632" personname="王栋" postname="分析员" workplace="3005" chedui="车间" education="0" maritalstatus="0" sex="0" workplaceName="调小运用车间" dutyGroupIndex="0"></return><return driverid="753823789" section="F31" workno="3009247" personname="陈雪龙" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823806" section="F31" workno="3008407" personname="梁万举" postname="副司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823847" section="F31" workno="3012741" personname="田友良" homephone="18625526742" postname="汽车司机" workplace="3001" chedui="车间" zhidaozu="运用综合组" education="0" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753823859" section="F31" workno="3012931" personname="宋洋" postname="副司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823869" section="F31" workno="3009250" personname="崔海涛" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823874" section="F31" workno="3012361" personname="邵彦淇" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823876" section="F31" workno="3012722" personname="蒋义哲" handphone="15037186687" postname="副司机" workplace="3005" chedui="枢纽车队" zhidaozu="第五指导组" education="4" maritalstatus="0" sex="0" workplaceName="调小运用车间" dutyGroupIndex="0"></return><return driverid="753823894" section="F31" workno="1228" personname="徐凯" postname="司机" workplace="3008" education="0" maritalstatus="0" sex="0" workplaceName="其他" dutyGroupIndex="0"></return><return driverid="753823895" section="F31" workno="1001" personname="胡勇" postname="司机" workplace="3008" education="0" maritalstatus="0" sex="0" workplaceName="其他" dutyGroupIndex="0"></return><return driverid="753823915" section="F31" workno="3002432" personname="李彦刚" homephone="15136286101" handphone="14985354513" postname="动车组司机" workplace="3001" chedui="第五机车队" zhidaozu="第五指导组" education="0" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753823918" section="F31" workno="3012753" personname="王浩" homephone="18538317997" postname="动车组司机" workplace="3001" chedui="第五机车队" zhidaozu="第四指导组" education="1" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753823919" section="F31" workno="3009568" personname="宋昊" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823933" section="F31" workno="3008729" personname="王建波" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753823993" section="F31" workno="3001897" personname="杨超" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753824238" section="F31" workno="3011204" personname="顾卫东" postname="干部" workplace="3008" education="0" maritalstatus="0" sex="0" workplaceName="其他" dutyGroupIndex="0"></return><return driverid="753824283" section="F31" workno="3008766" personname="李石磊" postname="科长" workplace="3011" education="0" maritalstatus="0" sex="0" workplaceName="技术科" dutyGroupIndex="0"></return><return driverid="753825009" section="F31" workno="3008306" personname="李斌" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753825030" section="F31" workno="3229316" personname="董延峰" postname="司机" workplace="3008" education="0" maritalstatus="0" sex="0" workplaceName="其他" dutyGroupIndex="0"></return><return driverid="753825031" section="F31" workno="3225025" personname="马建民" postname="司机" workplace="3008" education="0" maritalstatus="0" sex="0" workplaceName="其他" dutyGroupIndex="0"></return><return driverid="753825058" section="F31" workno="3009452" personname="刘静" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753825059" section="F31" workno="3012347" personname="杨勇" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753825060" section="F31" workno="3012347" personname="杨勇" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753825061" section="F31" workno="3009452" personname="刘静" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753825063" section="F31" workno="3012730" personname="刘高宾" postname="副司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753825073" section="F31" workno="3008529" personname="马卫忠" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753825074" section="F31" workno="3012412" personname="符强" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753825078" section="F31" workno="3012412" personname="符强" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753825079" section="F31" workno="3008529" personname="马卫忠" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753825090" section="F31" workno="3009269" personname="姬兴龙" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753825098" section="F31" workno="3008419" personname="刘闯兴" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753825173" section="F31" workno="3014446" personname="王鑫有" handphone="13781477399" postname="副司机" workplace="3002" address="西堡新居一号楼301" chedui="东二车队" zhidaozu="第一指导组" education="2" birthdate="1999-11-15T00:00:00+08:00" idcardnum="411421199911150010" nation="汉族" workcardnum="2066200144465" graduateschool="郑州铁路职业技术学院" graduatenum="108431202006002959" maritalstatus="0" zip="476800" homeaddress="西堡新居一号楼301" inworktime="2020-09-17T00:00:00+08:00" sex="0" workplaceName="客运车间" dutyGroupIndex="0"></return><return driverid="753825204" section="F31" workno="3002688" personname="付雷" postname="内燃司机" workplace="3001" chedui="第三机车队" zhidaozu="第一指导组" education="1" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753825303" section="F31" workno="3008974" personname="赵长永" handphone="13503868155" workplace="3008" education="0" maritalstatus="0" sex="0" workplaceName="其他" dutyGroupIndex="0"></return><return driverid="753825304" section="F31" workno="3010219" personname="赵智贤" workplace="3008" education="0" maritalstatus="0" sex="0" workplaceName="其他" dutyGroupIndex="0"></return><return driverid="753825336" section="F31" workno="3014529" personname="郑文博" handphone="18239935014" postname="副司机" workplace="3002" address="河南省商丘市梁园区凯旋北路208号6号楼3单元502号" chedui="南线车队" zhidaozu="第九指导组" education="1" birthdate="1999-05-30T00:00:00+08:00" idcardnum="411402199905303018" nation="汉族" workcardnum="2066200145299" graduateschool="郑州铁路职业技术学院" techlevel="中级工" maritalstatus="0" zip="450000" homeaddress="河南省商丘市梁园区凯旋北路208号6号楼3单元502号" inworktime="2020-09-11T00:00:00+08:00" sex="0" workplaceName="客运车间" dutyGroupIndex="0"></return><return driverid="753825520" section="F31" workno="3014642" personname="崔义民" handphone="18330833275" postname="副司机" workplace="3003" address="河北省衡水市阜城县崔庙镇崔庙村" chedui="北线车队" zhidaozu="第一指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825521" section="F31" workno="3014682" personname="李天翔" handphone="15038012357" postname="副司机" workplace="3003" address="郑州市金水区南阳路230号4号楼30号" chedui="北线车队" zhidaozu="第二指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825522" section="F31" workno="3014685" personname="林春铁" handphone="19832188790" postname="副司机" workplace="3003" address="河北省邢台市清河县谢炉镇刁楼庄61号" chedui="东一车队" zhidaozu="第三指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825523" section="F31" workno="3014692" personname="刘明阳" handphone="19138101971" postname="副司机" workplace="3003" address="河北省唐山市路北区果园乡许各寨8-1-101" chedui="北线车队" zhidaozu="第七指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825524" section="F31" workno="3014711" personname="唐一奇" handphone="18539918923" postname="副司机" workplace="3003" address="河南省郑州市二七区保全街九十五号院三号楼三十号" chedui="北线车队" zhidaozu="第六指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825525" section="F31" workno="3014712" personname="唐毅飞" handphone="15824806314" postname="副司机" workplace="3003" address="河南省许昌市魏都区新兴街道兴华路兴华嘉园" chedui="东二车队" zhidaozu="第五指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825527" section="F31" workno="3014720" personname="王瑞程" handphone="18939594090" postname="副司机" workplace="3003" address="河南省漯河市召陵区燕林苑" chedui="东二车队" zhidaozu="第七指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825528" section="F31" workno="3014722" personname="王玺智" handphone="18703673715" postname="副司机" workplace="3003" address="郑州市管城区石化路中铁七局小区七号楼二单元九楼西户" chedui="北线车队" zhidaozu="第四指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825529" section="F31" workno="3014727" personname="王子恒" handphone="18838152967" postname="副司机" workplace="3003" address="河南省郑州市新郑市祥和开发小区华祥巷七号楼二单元四楼东户" chedui="东一车队" zhidaozu="第四指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825530" section="F31" workno="3014734" personname="邢赛威" handphone="13460588996" postname="副司机" workplace="3003" address="河南省许昌市鄢陵县安陵镇新庄村" chedui="北线车队" zhidaozu="第四指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825531" section="F31" workno="3014744" personname="杨润泽" handphone="15938743590" postname="副司机" workplace="3003" address="河南省郑州市二七区新圃西街18号院9号楼6楼39号" chedui="东二车队" zhidaozu="第七指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825532" section="F31" workno="3014747" personname="杨萧" homephone="17633723493" handphone="13243323675" postname="副司机" workplace="3003" address="河南省信阳市淮滨县芦集乡李新寨村瓦东组" chedui="北线车队" zhidaozu="第五指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825533" section="F31" workno="3014761" personname="张天祥" handphone="18595711773" postname="副司机" workplace="3003" address="郑州市二七区五里堡街道" chedui="北线车队" zhidaozu="第五指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825534" section="F31" workno="3014762" personname="张文博" handphone="17630872329" postname="副司机" workplace="3003" address="河南省许昌市魏都区解放路万里星河花园小区" chedui="东一车队" zhidaozu="第二指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825535" section="F31" workno="3014766" personname="张展鹏" handphone="17803872984" postname="副司机" workplace="3003" address="河南省郑州市新郑市郭店镇司洼村" chedui="东二车队" zhidaozu="第六指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825536" section="F31" workno="3014767" personname="张哲源" handphone="15093279320" postname="副司机" workplace="3003" address="河南省郑州市紫荆山路116号院七号楼一单元一户" chedui="北线车队" zhidaozu="第六指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825537" section="F31" workno="3014770" personname="赵胤清" handphone="15238395848" postname="电力副司机" workplace="3003" address="河南省郑州市二七区和平路铁道雅博园" chedui="北线车队" zhidaozu="第七指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825538" section="F31" workno="3014772" personname="郑杰栋" handphone="15981980827" postname="副司机" workplace="3003" address="河南省郑州市荥阳市京城花园28号四楼西" chedui="东一车队" zhidaozu="第六指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825539" section="F31" workno="3014779" personname="訾荣森" handphone="15249754528" postname="副司机" workplace="3003" address="河南省永城市条河镇肖庄村訾楼西组035号" chedui="东二车队" zhidaozu="第六指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825540" section="F31" workno="3014739" personname="薛辰浩" handphone="13592661103" postname="副司机" workplace="3003" address="河南省郑州市惠济区长柳路6号" chedui="东一车队" zhidaozu="第一指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825541" section="F31" workno="3014625" personname="白俊龙" handphone="15036038599" postname="副司机" workplace="3003" address="河南省郑州市经开区新安路锦程花园一号院16号楼一单元2504" chedui="东二车队" zhidaozu="第一指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825542" section="F31" workno="3014636" personname="陈昊" handphone="15978880859" postname="副司机" workplace="3003" address="河南省驻马店市驿城区安居新村二期4号楼一单元2楼西户" chedui="东二车队" zhidaozu="第一指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825543" section="F31" workno="3014691" personname="刘康" handphone="13633705691" postname="副司机" workplace="3003" address="河南省商丘市梁园区王楼乡袁店村" chedui="东三车队" zhidaozu="第二指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825544" section="F31" workno="3014703" personname="任浩然" handphone="18339676973" postname="副司机" workplace="3003" address="河南省驻马店市驿城区刘阁街道任马庄" chedui="东二车队" zhidaozu="第四指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825545" section="F31" workno="3014702" personname="屈恒浡" handphone="15639571265" postname="副司机" workplace="3003" address="河南省漯河市临颍县新建路533号" chedui="东一车队" zhidaozu="第三指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825546" section="F31" workno="3014624" personname="白嘉伟" handphone="15890665216" postname="副司机" workplace="3003" address="河南省郑州市二七区庆丰街1号院2号楼" chedui="东一车队" zhidaozu="第七指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825547" section="F31" workno="3014673" personname="李程" handphone="18437002079" postname="副司机" workplace="3003" address="河南省商丘市梁园区康城花园南区9号楼1105" chedui="东三车队" zhidaozu="第二指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825548" section="F31" workno="3014659" personname="何龙龙" handphone="13419736058" postname="副司机" workplace="3003" address="河南省驻马店市西平县祥和花苑小区4号楼2单元401" chedui="东一车队" zhidaozu="第二指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825549" section="F31" workno="3014675" personname="李豪" handphone="17839051692" postname="副司机" workplace="3003" address="河南省商丘市梁园区八一桥南苑小区南七排" chedui="东三车队" zhidaozu="第三指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825550" section="F31" workno="3014656" personname="郭毅铭" handphone="15038066831" postname="副司机" workplace="3003" address="河南省郑州市铁道京广家园25号1单元502" chedui="北线车队" zhidaozu="第一指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825551" section="F31" workno="3014663" personname="黄硕" handphone="17537121591" postname="副司机" workplace="3003" address="河南省郑州市桐柏北路开元新城银田花园4号楼3单元4332" chedui="东二车队" zhidaozu="第六指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825552" section="F31" workno="3014660" personname="何炜" handphone="13069327718" postname="副司机" workplace="3003" address="河南省开封市尉氏县城关镇西城墙街11号" chedui="东二车队" zhidaozu="第六指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825553" section="F31" workno="3014662" personname="胡醒龙" handphone="15660955696" postname="副司机" workplace="3003" address="河南省信阳市浉河区五星路二组" chedui="东二车队" zhidaozu="第五指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825554" section="F31" workno="3014631" personname="曹恪" handphone="18337069007" postname="电力副司机" workplace="3003" address="河南省商丘市梁园区新建路124号" chedui="东一车队" zhidaozu="第二指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825555" section="F31" workno="3014633" personname="曹政天" handphone="18595426983" postname="副司机" workplace="3003" address="郑州市二七区保全街铁道京广家园二期18号楼1单元804" chedui="东一车队" zhidaozu="第一指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825556" section="F31" workno="3014684" personname="李跃辉" handphone="15188323994" postname="副司机" workplace="3003" address="河南省郑州市高新区轻工业大学家属院5号楼801" chedui="北线车队" zhidaozu="第二指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825557" section="F31" workno="3014696" personname="孟宪澍" handphone="13838056780" postname="副司机" workplace="3003" address="河南省郑州市二七区碧云路16号院5号楼三单元五楼" chedui="东二车队" zhidaozu="第三指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825558" section="F31" workno="3014666" personname="贾明伦" handphone="15638862965" postname="副司机" workplace="3003" address="河南省郑州市二七区棉纺东路鑫苑国际城市花园27号楼2单元3楼" chedui="北线车队" zhidaozu="第七指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825559" section="F31" workno="3014709" personname="史瑞琪" handphone="13723243244" postname="副司机" workplace="3003" address="河南省开封市尉氏县城关镇人民西路交警大队对面二栋三单元二楼西" chedui="北线车队" zhidaozu="第一指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825560" section="F31" workno="3014700" personname="邱泓超" handphone="19937159431" postname="副司机" workplace="3003" address="河南省开封市顺河回族区汴京路南街11号楼4单元6号" chedui="北线车队" zhidaozu="第八指导组" education="3" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825613" section="F31" workno="3014334" personname="李博文" handphone="18336983835" postname="副司机" workplace="3002" address="河南省商丘市民权县" chedui="北线车队" zhidaozu="第五指导组" education="2" birthdate="1998-05-05T00:00:00+08:00" idcardnum="411421199805050112" nation="汉" workcardnum="2066200143347" graduateschool="郑州铁路职业技术学院" graduatenum="108431202006002000" techlevel="四级" maritalstatus="0" zip="450000" homeaddress="河南省郑州市管城区紫荆山南路五里堡社区西堡新居" inworktime="2020-10-10T00:00:00+08:00" sex="0" workplaceName="客运车间" dutyGroupIndex="0"></return><return driverid="753825693" section="F31" workno="3009061" personname="张勇" postname="司机" workplace="3017" education="0" maritalstatus="0" sex="0" workplaceName="北整备车间" dutyGroupIndex="0"></return><return driverid="753825957" section="F31" workno="3014809" personname="秦维良" handphone="15081499128" postname="副司机" workplace="3003" chedui="东二车队" zhidaozu="第三指导组" education="5" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825958" section="F31" workno="3014803" personname="罗正泉" handphone="13102740622" postname="副司机" workplace="3003" chedui="东一车队" zhidaozu="第七指导组" education="5" maritalstatus="0" sex="0" workplaceName="货运车间" dutyGroupIndex="0"></return><return driverid="753825965" section="F31" workno="3012797" personname="郭运龙" homephone="13526662377" handphone="14985357293" postname="动车组司机" workplace="3001" chedui="第二机车队" zhidaozu="第四指导组" education="1" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753825978" section="F31" workno="3001662" personname="侯蕴韬" postname="司机" workplace="3002" chedui="地勤车队" zhidaozu="第一指导组" education="0" maritalstatus="0" sex="0" workplaceName="客运车间" dutyGroupIndex="0"></return><return driverid="753825988" section="F31" workno="3014710" personname="孙才硕" homephone="17639640558" postname="动车组副司机" workplace="3001" chedui="第二机车队" zhidaozu="第二指导组" education="0" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753825989" section="F31" workno="3014695" personname="刘雨祥" homephone="17692600869" postname="动车组副司机" workplace="3001" chedui="第二机车队" zhidaozu="第四指导组" education="0" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753825992" section="F31" workno="3014738" personname="许值浩" homephone="13849011105" postname="动车组副司机" workplace="3001" chedui="第一机车队" zhidaozu="第二指导组" education="0" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753825994" section="F31" workno="3014796" personname="李紫阳" homephone="15127557660" postname="动车组副司机" workplace="3001" chedui="第二机车队" zhidaozu="第四指导组" education="0" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753825995" section="F31" workno="3014783" personname="董浩浩" homephone="13012040812" postname="动车组副司机" workplace="3001" chedui="第二机车队" zhidaozu="第四指导组" education="0" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753825996" section="F31" workno="3014785" personname="冯轩" homephone="18503176746" postname="动车组副司机" workplace="3001" chedui="第二机车队" zhidaozu="第一指导组" education="0" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753825997" section="F31" workno="3014786" personname="付志伟" homephone="17398987571" postname="动车组副司机" workplace="3001" chedui="第二机车队" zhidaozu="第一指导组" education="1" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753825998" section="F31" workno="3014787" personname="付子康" homephone="15731188122" postname="动车组副司机" workplace="3001" chedui="第二机车队" zhidaozu="第四指导组" education="0" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753825999" section="F31" workno="3014799" personname="刘梓恒" homephone="13473233258" postname="动车组副司机" workplace="3001" education="0" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753826000" section="F31" workno="3014801" personname="禄麒通" homephone="18337467917" postname="动车组副司机" workplace="3001" chedui="第二机车队" zhidaozu="第四指导组" education="0" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753826001" section="F31" workno="3014804" personname="马嘉举" homephone="15640568559" postname="动车组副司机" workplace="3001" education="0" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753826002" section="F31" workno="3014782" personname="程昱" homephone="15237697129" postname="学员" workplace="3005" chedui="枢纽车队" zhidaozu="第四指导组" education="0" maritalstatus="0" sex="0" workplaceName="调小运用车间" dutyGroupIndex="0"></return><return driverid="753826003" section="F31" workno="3014798" personname="刘威振" homephone="17778256701" postname="学员" workplace="3008" education="0" maritalstatus="0" sex="0" workplaceName="其他" dutyGroupIndex="0"></return><return driverid="753826004" section="F31" workno="3014807" personname="牛若武" homephone="15131137132" postname="动车组副司机" workplace="3001" chedui="第一机车队" zhidaozu="第四指导组" education="0" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753826005" section="F31" workno="3014822" personname="魏江傲" homephone="15176339860" postname="动车组副司机" workplace="3001" chedui="第一机车队" zhidaozu="第二指导组" education="0" maritalstatus="0" sex="0" workplaceName="动车运用车间" dutyGroupIndex="0"></return><return driverid="753826006" section="F31" workno="3014824" personname="徐泽浩" homepho"""
    data2 = [
        {
            "api": "his",
            "type": "XML",
            "name": "hospital",
            "class_name": "cata",
            "off": "true"
        },
        {
            "api": "*",
            "type": "JSON",
            "name": "kpfnsrsbh|Xsfmc|gmfmc|Gmfmc|Xfmc|Gfmc|Xsfnsrsbh|Gmfnsrsbh|Lzfpdm|Lzfphm|xsfmc|gmfnsrsbh|xsfnsrsbh|xfNsryhzh|fphm|fpdm|nsrmc|nsrsbh|Gfsbh|xfsbh|xsfsbh|gmfsbh|Dqnsrsbh|xhfdz|NSRSBH|NSRMC",
            "class_name": "开票方纳税人识别号|销售方名称|购买方名称|购买方名称|销售方名称|购买方名称|销售方纳税人识别号|购买方纳税人识别号|发票号码|发票代码|销售方名称|购买方纳税人识别号|销售方纳税人识别号|销售方纳税人银行账号|发票号码|发票代码|纳税人名称|纳税人识别号|购买方识别号|销售方识别号|销售方识别号|购买方识别号|地区纳税人识别号|销货方地址|纳税人识别号|纳税人名称",
            "off": "true"
        },
        {
            "api": "http://10.96.5.31:8082/api/hrmsOrgBasicInfo/list",
            "type": "JSON",
            "name": "cphm|escMc|escSbh|gfMc|xfMc|kpfNsrsbh|fpdm|fphm",
            "class_name": "车牌号|esc名称|esc识别号|购方名称|销售方名称|开票方识别号|发票代码|发票号码",
            "off": "true"
        }
    ]

    sen_dic = get_data(data2)
    print(sen_dic)
    url = "http://10.96.5.31:8082/api/hrmsOrgBasicInfo/list"

    """
    cphm|escMc|escSbh|gfMc|xfMc|kpfNsrsbh|fpdm|fphm
    车牌号|esc名称|esc识别号|购方名称|销售方名称|开票方识别号|发票代码|发票号码
    """
    dict = {
        "success": "true",
        "errorCode": "0",
        "total": 0,
        "data": [
            {
                "tzdbh": "5101292303005528",
                "tzdzt": 5,
                "kjyf": "202303",
                "tkrq": "2023-03-29 00:00:00",
                "fplxdm": "004",
                "szlb": "1",
                "yfpdm": "5100204160",
                "yfphm": "02102542",
                "ykprq": "2023-02-20 00:00:00",
                "hjje": -1427600,
                "sl": 0.13,
                "se": -185588,
                "xhfsbh": "91510000902667031J",
                "xfMc": "四川天邑康和通信股份有限公司",
                "xsfswjgdm": "15101299000",
                "xsfswjgmc": "国家税务总局大邑县税务局第二税务分局",
                "gmfsbh": "91140000743502490G",
                "gfMc": "中国移动通信集团山西有限公司晋中分公司",
                "gmfswjgdm": "11424013600",
                "gmfswjgmc": "国家税务总局晋中市榆次区税务局第二税务分局",
                "sqf": "0",
                "thyy": "",
                "jqbh": "661709856841",
                "sqdbh": "661709856841230329152835",
                "jbrdm": "system",
                "jbrmc": "system",
                "bmbbbh": "48.0",
                "range": 1,
                "waitRec": "Y",
                "yddk": "0",
                "dkbdbs": "0",
                "czsj": "2023-03-29 15:26:34",
                "xsfswjgdmcx": "15101299000",
                "gmfswjgdmcx": "11424013600",
                "slbz": "0",
                "kpjh": "1",
                "xxblx": "0",
                "dslbz": "0",
                "sqsm": "0000000100",
                "sqjg": "N5",
                "sjly": "0",
                "tspz": "",
                "lpssyf": "202302",
                "gmfdzdh": "山西省晋中市榆次区东顺城街3号 0354-3069516",
                "gmfyhzh": "中国工商银行晋中市分行道北支行0508012009022119858",
                "rubricInfoDetails": [
                    {
                        "tzdbh": "5101292303005528",
                        "xh": 0,
                        "mc": "*通信接入设备*智能网关",
                        "ggxh": "TEWA-862G",
                        "jldw": "台",
                        "shul": "-10000",
                        "dj": "142.760000000000000",
                        "je": -1427600,
                        "sl": 0.13,
                        "se": -185588,
                        "spbm": "1090506010000000000",
                        "yhzcbs": "0",
                        "czsj": "2023-03-29 15:26:34",
                        "hsbz": "N",
                        "qyspbm": "0705",
                        "check": "true"
                    }
                ],
                "rubricInfoDetailsQd": [],
                "startRow": 0,
                "endRow": 0,
                "swjgdm": "15100000000",
                "gmfdjxh": "11140098000000128357",
                "xsfdjxh": "10115101000068219929",
                "sqfisJyqy": "0",
                "update": "false"
            }
        ]
    }
    abc3 = json.dumps(dict, ensure_ascii=False)
    # url="http://10.96.5.31:8082/api/hrmsOrgBasicInfo/list"
    sen_data, abc3 = match_data(abc3, sen_dic, url)
    print(sen_data)
    print(abc3)

    """
    纳税人识别号或社会统一信用代码|纳税人名称或公司名称|纳税人名称或公司名称|纳税人名称或公司名称|纳税人名称或公司名称|纳税人名称或公司名称|纳税人识别号或社会统一信用代码|纳税人识别号或社会统一信用代码|发票代码|发票号码|纳税人名称或公司名称|纳税人识别号或社会统一信用代码|纳税人识别号或社会统一信用代码|销售方纳税人银行账号|发票号码|发票代码|纳税人名称|纳税人识别号|购买方识别号|销售方识别号|销售方识别号|购买方识别号|地区纳税人识别号|销货方地址|纳税人识别号|纳税人名称
    
    """
