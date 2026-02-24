一些踩坑记录

# X(Twitter)
反爬虫机制简直丧心病狂, 任何第三方库都不靠谱, 直接上浏览器.
我用了一个专门的账号登陆, 主要不是安全的考虑, 而是真的不能关注像elon musk这样的人, 整天发一些毫无营养的东西, 完全浪费我
的token

# 被AI蠢哭的记录
- 我知道为什么默认不让agent碰gitignore里的文件了, 它改坏了我没法回退, 艹
-AI非常执着的根据fetcher里的prompt, 把fetcher返回里的所有column hard code进append_raw_log tool里
(maybe有一点点道理是因为这样可以保证append_raw_log 最终column的顺序是确定的?)
