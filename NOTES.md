一些Learnings

# X(Twitter)
反爬虫机制简直丧心病狂, 任何第三方库都不靠谱, 直接上浏览器.
我用了一个专门的账号登陆, 主要不是安全的考虑, 而是真的不能关注像elon musk这样的人, 整天发一些毫无营养的东西, 完全浪费我
的token

# 被AI蠢哭的记录
- 我知道为什么默认不让agent碰gitignore里的文件了, 它改坏了我没法回退, 艹
- AI非常执着的根据fetcher里的prompt, 把fetcher返回里的所有column hard code进append_raw_log tool里
(maybe有一点点道理是因为这样可以保证append_raw_log 最终column的顺序是确定的?)

# python directory structure
摸索出一种比较好的structure
```
src/
  resources/
    config file examples
  package/
    main.py
    modules/
```
这样的话可以很方便的安装成一个脚本, 并且package不会跟别的包冲突

# dotenv
- `dotenv`寻找`.env`的逻辑很奇怪, 当安装成一个脚本时,它有时不会从当前目录加载.env文件
- `dotenv`似乎也不好设置数据类型 (例如数组)
- 所以我比较倾向于用toml来管理配置, 并且把example文件放在resources里
- cronjob的environment variable也很麻烦, 如果不想在cronjob来source一堆文件或者export一堆variable, 
  那么可以用inject的方式把toml里的变量注入到environment variable里