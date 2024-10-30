# -*- coding:utf-8 -*-
# @FileName  :cl_url_merge.py
# @Time      :2023-06-13 15:10
# @Author    :Rzc
#
from urllib.parse import urlparse
import shutil
import json
import pickle
class TrieNode:
    def __init__(self):
        self.children = {}

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def add_uri(self,domain,path):
        node = self.root
        #获取单个应用和路径
        # 获取当前进入的路径中的索引为1的值
        splits = path.split('/')
        f_u = splits[1]
        length = len(splits)
        # 添加域名
        if domain not in node.children: #为空字典
            node.children[domain] = TrieNode()
        node = node.children[domain]#取出存在域名 存在的字典信息
        # 添加长度对应的字典项
        length=str(length)
        #取出的域名之后 node就变成了 一个字典，所以不包含了 clildren属性 这边判断一下 node是否为字典，如果是则给他重新带上children属性
        if isinstance(node,dict):
            nodes=TrieNode()
            nodes.children=node
            node=nodes
        #判断 字段长度是否存在 node中
        if length not in node.children:
            node.children[length] = []
            node.children[length].append({
                "f_u": f_u,
                "uri": path,
                "url_c": "",
                "courl": 1,
            })
            return path, 1
        else:
            # 查找相似的字典项并合并或添加新项
            length_node = node.children[length]
            found = False
            for item in length_node:
                if item["uri"]==path:
                    if item["url_c"]!="":
                        return item["url_c"],item["courl"]
                    else:
                        return path,item["courl"]
                elif f_u== item["f_u"]:
                    url_c=self.is_similar_uri(item["uri"], splits)
                    if url_c:
                        item["courl"]+=1
                        if item["url_c"]=="":
                            found = True
                            item["url_c"]=url_c
                            
                            
                            #return url_c,self.get_dictionary(), item["courl"]
                            return url_c, item["courl"]
                        return url_c,item["courl"]

                    else:
                        continue
                # else:
                #     url_c=item["url_c"]
                #     if url_c:
                #         #return item["url_c"], self.get_dictionary(), item["courl"]
                #         return item["url_c"],item["courl"]
                    # else:
                    #     #return path, self.get_dictionary(), item["courl"]
                    #     return path, item["courl"]


            if not found:
                node.children[length].append({
                    "f_u": f_u,
                    "uri": path,
                    "url_c": "",
                    "courl": 1,
                    
                })
                #如果没有 found 即没有合并
                #return path,self.get_dictionary(),1
                return path, 1

    def is_similar_uri(self, uri1, path2):
        # 根据您的要求进行相似度判断
        # 这里是您之前给出的代码的实现
        # 您可以根据需要进行调整
        path1 = uri1.split("/")

        url_merge = f"/{path2[1]}/"
        count = 0
        ck = 0

        for i in range(2, min(len(path1), len(path2))):
            if path1[i] != path2[i]:
                count += 1
                url_merge += f"{{p{count}}}/"
                ck += 1
                if count > 6:
                    break
            else:
                if (path1[i] != "" and path2[i] != "") or (path1[i]=="" and path2[i]==""):
                    url_merge +=f"{path1[i]}/"
                    ck += 1

        if (path1[-1] != "" and path2[-1] == "") or (path2[-1] == "" and path1[-1] != ""):
            ck = 0
            count = 7
            url_merge = ""

        if ck and 0 < count <= 6:
            url_c = url_merge[:-1]
        else:
            url_c = ""

        return url_c


    def get_dictionary(self):
        """
        查看 字典中信息
        :return:
        """
        return self.root.children

    def dump_file_pkl(self, filename):
        """
        写入pkl数据中
        :param filename:
        :return:
        """
        temp_filename=filename+".temp"
        with open(temp_filename, 'wb') as file:
            pickle.dump(self.get_serializable_dictionary(), file)
        #移动副本到新的路径文件明
        shutil.move(temp_filename,filename)
    def dump_file_json(self, filename):
        """
        写入json数据中
        :param filename:
        :return:
        """
        temp_filename = filename + ".temp"
        with open(temp_filename, 'w',encoding="utf-8") as file:
            json.dump(self.get_serializable_dictionary(), file,ensure_ascii=False)
        shutil.move(temp_filename, filename)


    def get_serializable_dictionary(self):
        return self.serialize_node(self.root.children)

    def serialize_node(self, node):
        """
        存储信息数据
        :param node:
        :return:
        """
        serialized = {}
        for key, value in node.items():
            if isinstance(value, TrieNode):
                serialized[key] = self.serialize_node(value.children)
            else:
                serialized[key] = value
        return serialized

    #装载pkl数据文件
    def load_file_json(self, filename):
        """
        装载之前json的数据信息
        :param filename:
        :return:
        """
        with open(filename, 'rb') as file:
            data = json.load(file)
            #data=pickle.load(file)
            self.root.children= self.deserialize_node(data)

    def load_file_pkl(self, filename):
        """
        装载之前pkl的数据信息
        :param filename:
        :return:
        """
        with open(filename, 'rb') as file:
            data=pickle.load(file)
            self.root.children= self.deserialize_node(data)

    def deserialize_node(self, data):
        """
        数据详情
        :param data:
        :return:
        """
        nodes={}
        #node = TrieNode()
        for key, value in data.items():
            nodes[key] = value
        return nodes


    def match_url(self,merge, url, counts, app):
        """
        只管做对比，无需进行存储数据
        :param merge: main_json中进行合并的数据
        :param url:
        :param counts:
        :return:
        """
        count = str(counts)
        courl = 1
        url_split = url.split("/")
        f_u = url_split[1]
        # 判断counts是否存在
        sub_dict_cache = merge.get(app, {}).get(count)
        if sub_dict_cache is None:
            return url, courl
        sub_dict = [(item, item.get('uri').split('/')) for item in sub_dict_cache]
        # 遍历子字典重得元素
        for item, uri_split in sub_dict:
            # 判断f_u是否相同
            if item.get("f_u") == f_u:
                if counts == 3:
                    count = 0
                    url_merge = "/" + f_u + "/"
                    if url_split[2] and uri_split[2]:
                        count += 1
                        url_merge += "{p%s}" % count + "/"
                    if count:
                        url_c = url_merge[:-1]
                        courl = item.get("courl")
                        return url_c, courl
                else:
                    url_c = self.com_url(url_split, uri_split, url, f_u)  # 进行合并处理
                    courl = item.get("courl")
                    return url_c, courl
        return url, courl

    def com_url(self,url_split, uri_split, url, f_u):

        url_merge = "/" + f_u + "/"
        ck = 0
        count = 0
        for k in range(2, len(uri_split)):
            # 对比
            if uri_split[k] == url_split[k]:
                url_merge += uri_split[k] + "/"
                ck += 1
            else:
                if uri_split[k] != "" and url_split[k] != "":
                    count += 1
                    url_merge += "{p%s}" % count + "/"
                    ck += 1
                    if count > 6:
                        break
        if (url_split[-1] != "" and uri_split[-1] == "") or (uri_split[-1] == "" and url_split[-1] != ""):
            ck = 0
            count = 7
        if ck and 0 < count <= 6:
            # 判断相同的添加，和不同的合并
            url_c = url_merge[:-1]
        else:
            url_c = url
        return url_c

    def urlc(self,url_m, http_url, destport, app):
        if not app:
            app = ""
        if destport == 80:
            # 然后进行接口合并
            url_c = "http://" + app + url_m
            url = "http://" + app + http_url
        else:
            url_c = "http://" + app + ":" + str(destport) + url_m
            url = "http://" + app + ":" + str(destport) + http_url
        return url_c, url
if __name__ == '__main__':

    # 测试示例
    trie = Trie()
    #
    urls = [
        "/ebus/00000000000_nw_dzfpfwpt/yp/bgskssq/v1/cxDqSkssq",
        "/ebus/00000000000_nw_dzfpfwpt/yp/nasdsada/v1/qqqdadad",
        "/other/123456",
        "/ebus/00000000000_nw_dzfpfwpt/yp/bgskssq/v1/abcd",
        "/ebus/00000000000_nw_dzfpfwpt/yp/nasdsadadada/v1/qqqdadadddd",
        "/ebus/00000000000_nw_dzfpfwpt/yp/xyz",
        "/ebus/00000000000_nw_dzfpfwpt/yp/nasdsadadada/v1/qqqdadadddd",
        "/ebus/00000000000_nw_dzfpfwpt/yp/nasdsadadada/v1/qqqdadadddd",
    ]
    app="www.example.com"
    for url in urls:
        url_c, courl=trie.add_uri(app,url)
        print(url_c)

    app2="wyww.sedo.com"
    urls2=[
        "/cn/about-us/company-overview/",
        "/cn/about-us/company-overviewaa/",
        "/cn/about-uss/company-overview/",
        "/cn/about-usss/company-overview/"

    ]

    for url in urls2:
        url_c, courl=trie.add_uri(app2,url)
        print(url_c)

        print(courl)
    #
    #trie.dump_file_pkl("./test.pkl")
   # trie.dump_file_json("./test.json")
