import json
import requests
import pymysql
import operator
from contextlib import contextmanager
from config import Config


class Bili:
    def __init__(self):
        self.query_sql = 'select * from Up'
        """
        pn: 第几页
        ps: 一页有多少数据(B站默认为一页25)
        """
        self.friends_url = 'https://api.bilibili.com/x/relation/' \
                           'followings?vmid={}&pn={}&ps={}&or' \
                           'der=desc&jsonp=jsonp&callback=__jp6'
        self.headers = {
            'referer': "https://space.bilibili.com/{}".format(Config.BID),
            'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit'
                          '/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36'
        }
        self.up_url = "https://space.bilibili.com/ajax/member/ge" \
                      "tSubmitVideos?mid={}&page=1&pagesize=1"
        self.old_friends = {}  # 这是数据库查出来的
        self.new_friends = {}  # 这个是请求API的，
        # 后面两者对比，可以得到新关注的,也可以得到你取关的
        self.email_message = []
        self.email = Config.EMAIL

    def __enter__(self):
        self.conn = pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database='bilibili',
            charset='utf8'
        )
        # 游标
        self.cursor = self.conn.cursor()
        self.cursor.execute(self.query_sql)  # 执行 self.query_sql语句
        self.old_friends_data = self.cursor.fetchall()  # 拿到数据
        for id, title, author, aid in self.old_friends_data:
            self.old_friends[id] = [id, title, author, aid]
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            print(exc_val)
        self.cursor.close()
        self.conn.close()
        return True

    def run(self):
        friends = self._get_friends()
        for friend in friends:
            mid = friend['mid']
            uname = friend['uname']
            up = requests.get(self.up_url.format(mid), headers=self.headers)
            info = json.loads(up.text)
            info = info['data']['vlist']
            if info:
                title = info[0]['title']
                aid = info[0]['aid']
                self.new_friends[mid] = [mid, title, uname, str(aid)]
        self._judge_is_new()
        if len(self.email_message) != 0:
            self._send_email()

    # 有两个列表，一个是请求下来的，一个是数据库查询出来的
    # 比对 aid
    def _judge_is_new(self):
        for key, value in self.old_friends.items():
            if not self.new_friends.__contains__(key):
                self._delete_friend(value[0])
            else:
                if not operator.eq(value[3], self.new_friends[key][3]):
                    self._update_friends(self.new_friends[key])
                self.new_friends.pop(key)
        self._add_new_friends()

    # 删除不关注的up主
    def _delete_friend(self, mid):
        with self._auto_commit():
            delete_sql = 'delete from Up WHERE id={}'.format(mid)
            self.cursor.execute(delete_sql)

    # 添加新的up主
    def _add_new_friends(self):
        with self._auto_commit():
            for id, title, author, aid in self.new_friends.values():
                insert_sql = "insert into Up VALUES (%s,%s,%s,%s)"
                self.cursor.execute(insert_sql, (id, title, author, aid))

    # 更新信息，并且发邮件
    def _update_friends(self, value):
        with self._auto_commit():
            print(value)
            update_sql = "update Up set title=%s,author=%s,aid=%s WHERE id=%s"
            self.cursor.execute(update_sql, (value[1], value[2], value[3], value[0]))
            self.email_message.append(value)

    # 得到关注列表
    def _get_friends(self):
        friends = []
        for i in range(1, 6):
            data = requests.get(self.friends_url.format(Config.BID, i, 50), headers=self.headers)
            data = json.loads(data.text[6:-1])
            friends.append(data)
            if len(data['data']['list']) != 50 or len(data['data']['list']) == 0:
                break
        friends = [friend['data']['list'] for friend in friends]
        data = []
        for friend in friends:
            for each in friend:
                data.append(each)
        return data

    # 发邮件
    def _send_email(self):
        data = list(zip(*self.email_message))
        msg = '更新了！\n'
        title = ','.join(data[2])
        msg = msg + '\n'.join(data[1])
        post_data = {
            'msg': msg,
            'title': title,
            'to': self.email
        }
        requests.post('http://{}{}'.format(
            Config.EMAIL_SERVER_IP, Config.EMAIL_SERVER_URL),
            data=json.dumps(post_data))

    @contextmanager
    def _auto_commit(self):
        try:
            yield
            self.conn.commit()
        except Exception as e:
            print(e)
            self.conn.rollback()


if __name__ == '__main__':
    with Bili() as b:
        b.run()
