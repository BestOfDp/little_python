# bilibili_push
小爬虫——b站up主更新视频推送

创建的时候，传入两个参数，bid——你的B站id，email——你能收到的邮箱
里面有连数据库的，稍微注意下。
有问题提问吧（本来想开服务的，但是我们朋友们貌似没有这个需求）。

## 9-28
以前只能爬取少量的页数，现在修改成动态爬取，每次50个关注，一共5页，因为B站规定除了本人外只能查看他人5页的关注数
 
新添加 config.py 都是一些配置项，比如数据库，email推送的接口，自行导入吧。
