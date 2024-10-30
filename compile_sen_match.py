import regex as re
from field_match import *


def monitor_data(response, re_data, data, whitelist, fid_mch_off, sen_dic, url, data_dict, level_dic):
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
    cls_lst = []
    level_lst = []

    count = {}

    if response:
        if fid_mch_off == "true":
            # 字段识别
            sen_data, response = match_data(response, sen_dic, url)
        else:
            # 普通识别
            sen_data = filter_data(data, response, whitelist)

        if sen_data:
            #  添加分类标签
            msg_info, msg_count, response_max_level, tol, response_cls_lst = cls_level(sen_data, data_dict)
            total_info["响应体"] = msg_info
            total_count["响应体"] = msg_count
            info["响应体"] = tol
            if response_cls_lst:
                cls_lst.extend(response_cls_lst)
            if response_max_level:
                level_lst.append(response_max_level)
            count["响应体"] = {k: len(list(set(v))) for k, v in sen_data.items()}
            # total_info["响应体"] = {k: list(set(v)) for k, v in sen_data.items()}
            # total_count["响应体"] = {k: len(list(set(v))) for k, v in sen_data.items()}
            # info["响应体"] = {k: {"数量": len(list(set(v))), "内容": list(set(v))} for k, v in sen_data.items()}
    if re_data:
        if fid_mch_off == "true":
            sen_data, re_data = match_data(re_data, sen_dic, url)
        else:
            sen_data = filter_data(data, re_data, whitelist)

        if sen_data:
            msg_info, msg_count, request_max_level, tol, request_cls_lst = cls_level(sen_data, data_dict)
            total_info["请求体"] = msg_info
            total_count["请求体"] = msg_count
            info["请求体"] = tol
            if request_cls_lst:
                cls_lst.extend(request_cls_lst)
            if request_max_level:
                level_lst.append(request_max_level)
                count["请求体"] = {k: len(list(set(v))) for k, v in sen_data.items()}
            # total_info["请求体"] = {k: list(set(v)) for k, v in sen_data.items()}
            # total_count["请求体"] = {k: len(list(set(v))) for k, v in sen_data.items()}
            # info["响应体"] = {k: {"数量": len(list(set(v))), "内容": list(set(v))} for k, v in sen_data.items()}
    if level_lst:
        level = level_dic.get(max(level_lst))
    else:
        level= ""
    cls = list(set(cls_lst))
    return response, re_data, total_info, total_count, info,level,cls,count


def cls_level(sen_data, data_dict):
    total_info = {}
    total_count = {}
    info = {}
    level_lst = []
    cls_lst = []
    for k, v in sen_data.items():
        values = data_dict.get(k)  # 表示有这个标识的数据信息
        if values:
            cls = values["cls"]
            level = values["level"]

            level_lst.append(level)
            cls_lst.append(cls)

            level_ch = values["level_ch"]

            total_info.setdefault(cls, {}).setdefault(level_ch, {}).setdefault(k, list(set(v)))
            total_count.setdefault(cls, {}).setdefault(level_ch, {}).setdefault(k, len(list(set(v))))
            info.setdefault(cls, {}).setdefault(level_ch, {}).setdefault(k, {"数量": len(list(set(v))),
                                                                             "内容": list(set(v))})
    if level_lst:
        max_level = max(level_lst)
    else:
        max_level = 0
    cls_lst = list(set(cls_lst))
    return total_info, total_count, max_level, info, cls_lst


def filter_data(data, message, whitelist):
    da = {}
    for re_match in data:
        if re_match["name"]!="":
            an = re_match["name"].findall(message)
            if an:
                if re_match["rekey"] in whitelist:
                    worng_name = whitelist.get(re_match["rekey"])
                    an = set(an) - set(worng_name)
                    if not an:
                        continue

                da[re_match["rekey"]] = list(an)
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

    return sen_data


if __name__ == '__main__':
    '''"sensitive": "[{'name': '\\\\b((?:[1-6][1-9]|50)\\\\d{4}(?:18|19|20)\\\\d{2}(?:(?:0[1-9])|10|11|12)(?:(?:[
    0-2][1-9])|10|20|30|31)\\\\d{3}[\\\\dXx])\\\\b', 'rekey': '身份证', 'off': 1, 'class': '个人信息', 'level': '3'}, 
    {'name': '\\\\b(13[0-9]\\\\d{8}|14[01456879]\\\\d{8}|15[0-35-9]\\\\d{8}|16[2567]\\\\d{8}|17[0-8]\\\\d{8}|18[
    0-9]\\\\d{8}|19[0-35-9]\\\\d{8})\\\\b', 'rekey': '手机号', 'off': 1, 'class': '个人信息', 'level': '3'}, 
    {'name': '\\\\b(?:\\\\\"??)((?:[\\\\w-]+@[\\\\w\\\\-.]+\\\\.)(?:com|cn|net))(?:\\\\\"??|$)\\\\b', 'rekey': '邮箱', 
    'off': 1, 'class': '个人信息', 'level': '1'}, {'name': '\\\\b([\\\\u4e00-\\\\u9fa5]+(?:省|自治区|特别行政区)?[
    \\\\u4e00-\\\\u9fa5]*(?:市|自治州|盟|地区|区|县|旗)[\\\\u4e00-\\\\u9fa5]*[\\\\u4e00-\\\\u9fa5\\\\d\\\\-]*(
    ?:号|路|街道|村|大道|巷|弄|横路|中路|广场|里|栋|座|楼|院|组|段|排|屯|坊|处|庄|区域))\\\\b', 'rekey': '地址', 'off': 1, 'class': '个人信息', 
    'level': '3'}, {'name': '\\\\b([赵,钱,孙,李,周,吴,郑,王,冯,陈,楮,卫,蒋,沈,韩,杨,朱,秦,尤,许,何,吕,施,张,孔,曹,严,华,金,魏,陶,姜,戚,谢,邹,喻,柏,水,窦,章,
    云,苏,潘,葛,奚,范,彭,郎,鲁,韦,昌,马,苗,凤,花,方,俞,任,袁,柳,酆,鲍,史,唐,费,廉,岑,薛,雷,贺,倪,汤,滕,殷,罗,毕,郝,邬,安,常,乐,于,时,傅,皮,卞,齐,康,伍,余,元,卜,顾,孟,平,黄,
    和,穆,萧,尹,姚,邵,湛,汪,祁,毛,禹,狄,米,贝,明,臧,计,伏,成,戴,谈,宋,茅,庞,熊,纪,舒,屈,项,祝,董,梁,杜,阮,蓝,闽,席,季,麻,强,贾,路,娄,危,江,童,颜,郭,梅,盛,林,刁,锺,徐,丘,骆,
    高,夏,蔡,田,樊,胡,凌,霍,虞,万,支,柯,昝,管,卢,莫,经,房,裘,缪,干,解,应,宗,丁,宣,贲,邓,郁,单,杭,洪,包,诸,左,石,崔,吉,钮,龚,程,嵇,邢,滑,裴,陆,荣,翁,荀,羊,於,惠,甄,麹,家,封,
    芮,羿,储,靳,汲,邴,糜,松,井,段,富,巫,乌,焦,巴,弓,牧,隗,山,谷,车,侯,宓,蓬,全,郗,班,仰,秋,仲,伊,宫,宁,仇,栾,暴,甘,斜,厉,戎,祖,武,符,刘,景,詹,束,龙,叶,幸,司,韶,郜,黎,蓟,薄,
    印,宿,白,怀,蒲,邰,从,鄂,索,咸,籍,赖,卓,蔺,屠,蒙,池,乔,阴,郁,胥,能,苍,双,闻,莘,党,翟,谭,贡,劳,逄,姬,申,扶,堵,冉,宰,郦,雍,郤,璩,桑,桂,濮,牛,寿,通,边,扈,燕,冀,郏,浦,尚,农,
    温,别,庄,晏,柴,瞿,阎,充,慕,连,茹,习,宦,艾,鱼,容,向,古,易,慎,戈,廖,庾,终,暨,居,衡,步,都,耿,满,弘,匡,国,文,寇,广,禄,阙,东,欧,殳,沃,利,蔚,越,夔,隆,师,巩,厍,聂,晁,勾,敖,融,
    冷,訾,辛,阚,那,简,饶,空,曾,毋,沙,乜,养,鞠,须,丰,巢,关,蒯,相,查,后,荆,红,游,竺,权,逑,盖,益,桓,公,万俟,司马,上官,欧阳,夏侯,诸葛,闻人,东方,赫连,皇甫,尉迟,公羊,澹台,公冶,宗政,濮阳,
    淳于,单于,太叔,申屠,公孙,仲孙,轩辕,令狐,锺离,宇文,长孙,慕容,鲜于,闾丘,司徒,司空,丌官,司寇,仉,督,子车,颛孙,端木,巫马,公西,漆雕,乐正,壤驷,公良,拓拔,夹谷,宰父,谷梁,晋,楚,阎,法,汝,鄢,涂,钦,
    段干,百里,东郭,南门,呼延,归,海,羊舌,微生,岳,帅,缑,亢,况,后,有,琴,梁丘,左丘,东门,西门,商,牟,佘,佴,伯,赏,南宫,墨,哈,谯,笪,年,爱,阳,佟,第五,言,福][\\\\u4e00-\\\\u9fa5]{
    1,2})\\\\b', 'rekey': '姓名', 'off': 1, 'class': '个人信息', 'level': '1'}]",

    '''
