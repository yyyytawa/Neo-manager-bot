# Neo manager bot

> [!warning]
> 本机器人纯娱乐,请勿要求提供任何技术支持.

## 运行

1. 克隆本仓库
2. 补全依赖

```bash
uv sync
```

3. 安装适配器

```bash
uv run epsdk install
```

在弹出的交互式页面上选择 1 适配器,安装 `yunhu` 适配器.  

4. 补全文件
编辑 `config/config.toml`,填写你的 `bot_token` 和 `bot_id`.  

5. 运行

```bash
uv run epsdk run main.py
```

## 命令说明

> [!note]
> 此处"管理员"权限指群主/管理员/机器人自带的额外管理员名单,"真管理员"指"群主/管理员"  
> 引用消息优先级更高.  

### ping

测试机器人存活状态.  

/ping

### board

设置文本看板,若不填写参数则为取消看板.需要管理员权限.  

/board \[看板内容\]  

### mboard

设置 Markdown 格式的看板,若不填写参数则为取消看板.需要管理员权限.  

/mboard \[看板内容\]  

### hboard

设置 HTML 格式的看板,若不填写参数则为取消看板.需要管理员权限.  

/hboard \[看板内容\]  

### mute

禁言用户,需要管理员权限.

/mute <引用用户消息/用户 ID> [禁言时长(单位秒,不写默认 600s,云湖后端对禁言时长有限制.)]  

### kick

将用户踢出群聊,需要管理员权限.  

/kick <引用用户消息/用户 ID>  

### del

撤回指定消息,需要管理员权限.  

/del <引用消息>  

### banme

禁言自己十分钟.  

/banme

### adminadd

添加额外管理员,需要真管理员权限.  

/adminadd <用户 1 User ID> <用户 2 的 User ID>  

### adminlist

查看额外管理员列表.别想着注入了,全转义过了.  

/adminlist

### admindel

删除额外管理员,需要真管理员权限.  

/admindel <用户 1 User ID> <用户 2 User ID>  

### warn

警告用户,需要管理员权限.  

/warn <引用消息> \[原因\]  

### warndel

撤销用户最近的一次警告,需要管理员权限.  

/warndel <用户 ID>  

### warns

查看警告历史.  

/warns \[用户 ID\]  