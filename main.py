"""
my_erispulse_project 主程序

这是 ErisPulse 自动生成的主程序文件
"""

import asyncio
from datetime import datetime
import json
from ErisPulse import sdk
from ErisPulse.Core import Event
from ErisPulse.Core.Event import command,message,notice
from ErisPulse.Core import adapter

import copy
import time
import threading

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from _ep_types import Yunhu

class settings:
    max_warns = 20 # 最大警告次数

class BlacklistLevel:
    """
    黑名单暂行管理规定:

    I 类: 强制开启不可关闭

    II 类: 默认开启可选关闭

    III 类: 默认关闭可选开启

    特殊: 临时风控类
    """

    I = True
    II = True
    III = False


class blacklist: # 联防黑名单
    data = None # 初始为空
    level = BlacklistLevel.I

class HallOfShame: 
    """
    封神榜默认数据
    专门存储反智奇葩人物
    当然这个只是存默认设置
    """
    name = "[封神榜]"
    level = BlacklistLevel.II
    key = "HallOfShameBlacklist" # 数据库中键名
    can_view_group = [
        "big"
    ]

@sdk.lifecycle.on("core.init.complete")
async def get_yunhu_adapter(event):
    global yunhu
    yunhu = adapter.get("yunhu")

@sdk.lifecycle.on("core.init.complete")
async def init_mem_cache(event):
    global mem_cache
    mem_cache = mem_cache_cls()
    while True: # 定期清理过期缓存
        await asyncio.sleep(3600)
        mem_cache.cleanup_expired()

class mem_cache_cls:

    def __init__(self):
        self.cache = {}
        self.usage = {}
        self.max_ttl = 3600
        self.lock = threading.Lock()

    def get(self,name: str, default: any = None) -> any:
        """获取数据"""
        __NONE__ = object()
        if name in self.cache:
            self.usage[name] = time.time()
            return copy.deepcopy(self.cache[name])
        else:
            data = sdk.storage.get(name, __NONE__)
            if data is __NONE__:
                return default
            
            self.cache[name] = copy.deepcopy(data)
            self.usage[name] = time.time()
            return data

    def set(self, name: str, data: str | dict | list) -> None:
        """设置数据,注意这里会自动清理掉对应名称数据的缓存."""
        with self.lock:
            if name in self.cache:
                self.cache.pop(name)
                self.usage.pop(name)

            sdk.storage.set(name, data)

    def delete(self,name: str) -> None:
        '''删除数据'''
        with self.lock:
            if name in self.cache:
                self.cache.pop(name)
                self.usage.pop(name)

            sdk.storage.delete(name)

    def clean(self,name: str) -> None:
        '''清除缓存'''
        with self.lock:
            if name in self.cache:
                self.cache.pop(name)
                self.usage.pop(name)

    def cleanup_expired(self) -> None:
        """清理过期数据"""
        waiting_for_delete = []
        with self.lock:
            for key,value in self.usage.items():
                if time.time() - value >= self.max_ttl:
                    waiting_for_delete.append(key)

            
            if not waiting_for_delete:
                sdk.logger.debug("无过期键,无需清理.")
                return

            sdk.logger.debug(f"清理过期键 { waiting_for_delete }")
            for key in waiting_for_delete:
                self.cache.pop(key)
                self.usage.pop(key)

async def get_msg(event: Event, msg_id: str) -> dict:
    """使用 msg_id 获取消息"""
    token = sdk.config.getConfig("Yunhu_Adapter.accounts")['default']["token"]
    rsp = await sdk.client.get(f"https://chat-go.jwzhd.com/open-apis/v1/bot/messages?token={ token }&chat-id={ event.get_group_id() }&chat-type=group&message-id={ msg_id }&before=1")
    msg_tmp = (await rsp.json()).get("data", {}).get("list")
    if not msg_tmp:
        return
    msg = msg_tmp[0]
    if msg.get("msgId") != msg_id:
        return
    return msg

async def get_parent_msg_sender(event, msg_id: str) -> dict:
    msg = await get_msg(event, msg_id)
    if not msg:
        return
    return msg["senderId"]


def is_real_admin(event: Event) -> bool:
    """判断发送者是否为真的管理员/群主"""
    role = event.get_raw()["event"]["sender"]['senderUserLevel']
    return role in ["owner", "administrator"]

def is_admin(event) -> bool:
    """判断发送者是否为管理员/群主"""
    role = event.get_raw()["event"]["sender"]['senderUserLevel']
    if role in ["owner", "administrator"]:
        return True
    admin = mem_cache.get(event.get_group_id(),{}).get("admin", [])
    if event.get_user_id() in admin:
        return True
    
    return False

@command("ping", help="Ping")
async def ping_handler(event):
    """测试机器人是否启动"""
    await event.reply("Pong!", reply_to= event['message_id'])

@command("help", help = "帮助")
async def help_handler(event: Event):
    """获取帮助"""
    await event.reply("https://github.com/yyyytawa/Neo-manager-bot", reply_to = event["message_id"])

@command("board", help = "设置群看板")
async def board_handler(event: Event):
    if not is_admin(event):
        await event.reply("无权限!", reply_to = event["message_id"])
        return

    conv = event.conversation(timeout=60)

    # 询问用户看板类型
    content_type = await conv.choose("请选择看板类型:", ["文本", "Markdown", "HTML"])

    if content_type is None:
        await conv.say("超时,已取消!", reply_to = event["message_id"])
        conv.stop()
        return

    content_type_mapping = {
        0: "text",
        1: "markdown",
        2: "html"
    }
    content_type = content_type_mapping.get(content_type)

    # 询问看板内容
    await conv.say('请发送看板内容(发送"清空"/"clean"以清空看板):')
    content = await conv.wait()

    if content:
        content = content.get_text()
    else:
        await conv.say("请求超时!", reply_to = event["message_id"])
        conv.stop()
        return

    if content in ["清空", "clean"]:
        result = await yunhu.Send.To("group", event.get_group_id()).DismissBoard("local")
    else:
        result = await yunhu.Send.To("group", event.get_group_id()).Board("local", content = content, content_type = content_type)
    
    if result.get("status") == "ok":
        await event.reply("设置成功!", reply_to = event["message_id"])
    else:
        await event.reply(f"设置失败! msg: { result.get("message") }")
    
    conv.stop()

@command("kick", help = "踢出用户")
async def kick_handler(event):
    """踢出用户"""
    if not is_admin(event):
        await event.reply("无权限!", reply_to = event["message_id"])
        return
    parent_id = event.get_raw()["event"]["message"].get("parentId")
    if parent_id:
        on_kick_id = await get_parent_msg_sender(event, parent_id)
    elif event.get_command_args():
        on_kick_id = event.get_command_args()[0]
    else:
        await event.reply("参数错误!用法: /kick + 引用消息/用户 ID.", reply_to = event["message_id"])
        return

    result = await yunhu.Send.To("group", event.get_group_id()).Kick(on_kick_id)
    if result.get("status") == "ok":
        await event.reply("成功!", reply_to = event["message_id"])
    else:
        await event.reply(f"失败,msg: {result.get("message")}", reply_to= event["message_id"])

@command("mute", help = "禁言用户")
async def mute_handler(event):
    """禁言用户"""
    if not is_admin(event):
        await event.reply("无权限!", reply_to = event["message_id"])
        return
    parent_id = event.get_raw()["event"]["message"].get("parentId")
    args = event.get_command_args()

    if parent_id:
        on_mute_id = await get_parent_msg_sender(event, parent_id)
        if len(args) == 1:
            time = args[0]
        elif len(args) == 2:
            time = args[1]
        else:
            time = 600
        
    elif event.get_command_args():
        on_mute_id = event.get_command_args()[0]
        time = 600 if len(args) == 1 else args[1]
    else:
        await event.reply("参数错误!用法: /mute + 引用消息/用户 ID + 时长(不写默认 600s).", reply_to = event["message_id"])
        return

    result = await yunhu.Send.To("group", event.get_group_id()).Ban(on_mute_id, duration=int(time))
    if result.get("status") == "ok":
        if time == "0":
            reply = f"成功解除用户 {on_mute_id} 的禁言."
        elif time == "-1":
            reply = f"成功禁言用户 {on_mute_id} 永久."
        else:
            reply = f"成功禁言用户 {on_mute_id} {time}s."

        await event.reply(reply, reply_to = event["message_id"])
    else:
        await event.reply(f"失败,msg: {result.get("message")}", reply_to= event["message_id"])

@command("banme", help = "禁言自己")
async def banme_handler(event):
    """禁言用户"""
    result = await yunhu.Send.To("group", event.get_group_id()).Ban(event.get_user_id(), duration=600)
    if result.get("status") == "ok":
        await event.reply(f"恭喜 {event.get_user_id()} 被禁言 10min,不许找人解禁喵~", reply_to = event["message_id"])
    else:
        await event.reply(f"失败,msg: {result.get("message")}", reply_to = event["message_id"])

@command("adminadd", help="添加额外管理员列表", aliases=["添加管理员"])
async def admadd_handler(event):
    if not is_real_admin(event):
        await event.reply("无权限!", reply_to = event["message_id"])
        return
    args = event.get_command_args()
    if not args:
        await event.reply("缺少参数!用法: /adminadd <用户ID>", reply_to = event["message_id"])
        return
    args = [ uid for uid in args if len(uid) <= 20]
    group_id = event.get_group_id()
    admin_list = mem_cache.get(f"{group_id}.admin", [])
    admin_list = list(set(admin_list + args))
    if len(admin_list) > 100:
        await event.reply("长度超限!请先删除一部分管理员.", reply_to = event["message_id"])
        return
    mem_cache.set(f"{group_id}.admin", admin_list)
    await event.reply("添加成功!", reply_to = event["message_id"])

@command("admindel", help="删除额外管理员", aliases=["删除管理员"])
async def admindel_handler(event):
    if not is_real_admin(event):
        await event.reply("无权限!", reply_to = event["message_id"])
        return
    args = event.get_command_args()
    if not args:
        await event.reply("缺少参数!用法: /admindel <用户ID>", reply_to = event["message_id"])
        return
    group_id = event.get_group_id()
    admin_list = set(mem_cache.get(f"{group_id}.admin", []))
    admin_list.difference_update(args)
    admin_list = list(admin_list)
    if admin_list:
        mem_cache.set(f"{group_id}.admin", admin_list)
    else:
        mem_cache.delete(f"{group_id}.admin")
    await event.reply("删除成功!", reply_to = event["message_id"])

@command("adminlist", help = "查看管理员列表", aliases=["查看管理员列表"])
async def adminlist_handler(event):
    group_id = event.get_group_id()
    admin_list = mem_cache.get(f"{group_id}.admin",[])
    content = f"群 `{group_id}` 的管理员列表:\n"
    for user_id in admin_list:
        content += f"- {to_html_entities(user_id)}\n"
    content += f"\n总计: {len(admin_list)}"
    await event.reply(content, method = "Markdown", reply_to = event["message_id"])

def to_html_entities(text: str) -> str:
    """将每个字符转换为 HTML 数字实体"""
    return ''.join(f'&#{ord(c)};' for c in text)

@command("del", help = "撤回指定消息")
async def del_handler(event):
    if not is_admin(event):
        await event.reply("无权限!", reply_to = event["message_id"])
        return

    group_id = event.get_group_id()
    parent_id = event.get_raw()["event"]["message"].get("parentId")
    if not parent_id:
        await event.reply("请引用要撤回的消息!", reply_to = event["message_id"])
        return

    result = await yunhu.Send.To("group", group_id).Recall(parent_id)
    if result.get("status") == "ok":
        await event.reply("撤回成功!", reply_to = event["message_id"])
    else:
        await event.reply(f"失败,msg: { result.get("message") }", reply_to = event["message_id"])

@command("warn", help = "警告用户")
async def warn_handler(event):
    """警告用户"""
    if not is_admin(event):
        await event.reply("无权限!", reply_to = event["message_id"])
        return
    parent_id = event.get_raw()["event"]["message"].get("parentId")
    if not parent_id:
        await event.reply("参数错误!,用法: /warn <引用消息> [原因]", reply_to = event["message_id"])
        return
    group_id = event.get_group_id()
    parts = event.get_command_raw().split(maxsplit=1)
    reason = parts[1] if len(parts) > 1 else ""
    if len(reason) > 100:
        await event.reply("原因最多 100 字!", reply_to = event["message_id"])
        return

    reason = reason if reason else "未填写"
    msg_raw = await get_msg(event, msg_id= parent_id)
    payload = {
        "time": event.get_time(),
        "operator": event.get_user_id(),
        "reason": reason,
        "msg_raw": msg_raw
    }
    parent_msg_sender = await get_parent_msg_sender(event, msg_id = parent_id)
    data = mem_cache.get(f"warns:{group_id}:{parent_msg_sender}", [])
    data.insert(0, payload)
    if len(data) > settings.max_warns:
        data = data[:settings.max_warns]
    mem_cache.set(f"warns:{group_id}:{parent_msg_sender}", data)
    await event.reply(f"成功警告用户 {parent_msg_sender}.\n原因: {reason}.\n当前用户的警告次数为 {len(data)}.")

@command("warndel", help = "撤销最近一次的警告")
async def warndel_handler(event):
    """撤销最近的一次警告"""
    if not is_admin(event):
        await event.reply("无权限!", reply_to = event["message_id"])
        return
    parts = event.get_command_raw().split(maxsplit=1)
    user_id = parts[1] if len(parts) > 1 else ""
    if not user_id:
        await event.reply("参数错误!用法: /warndel <用户 ID>", reply_to = event["message_id"])
        return
    elif len(user_id) > 20:
        await event.reply("用户 ID 过长!", reply_to = event["message_id"])
        return

    warns = mem_cache.get(f"warns:{event.get_group_id()}:{user_id}", [])
    warns = warns[1:]
    if warns:
        mem_cache.set(f"warns:{event.get_group_id()}:{user_id}", warns)
    else:
        mem_cache.delete(f"warns:{event.get_group_id()}:{user_id}")
    await event.reply(f"成功撤销用户 {user_id} 最近的一次警告!")

@command("warns", help = "查看警告记录")
async def warns_handler(event):
    parts = event.get_command_raw().split(maxsplit=1)
    user_id = parts[1] if len(parts) > 1 else ""
    if not user_id:
        user_id = event.get_user_id()

    group_id = event.get_group_id()
    warns = mem_cache.get(f"warns:{group_id}:{user_id}", [])
    content = f"<details>{user_id} 在群 {group_id} 被警告信息\n"
    for warn in warns:
        warn_time = datetime.fromtimestamp(warn["time"]).strftime("%Y-%m-%d %H:%M:%S")
        warn_msg_raw = json.dumps(warn["msg_raw"], indent=2, ensure_ascii=False)
        content += f"警告时间: {warn_time}\n原因: {to_html_entities(warn["reason"])}\n操作者: {warn["operator"]}\n被警告的信息元数据:\n{to_html_entities(warn_msg_raw)}\n"
    content += f"总计: {len(warns)} 条.</details>"
    await event.reply(content, method = "Markdown", reply_to = event["message_id"])

# ============================================================
#                        黑名单相关
# ============================================================

@message.on_group_message()
async def mute_blacklist_user(event: Event):
    sender_id = event.get_user_id()
    group_id = event.get_group_id()
    msg_id = event["message_id"]
    need_recall = False
    if sender_id in blacklist.data:
        sdk.logger.info(f"发现联防黑名单用户 {sender_id},准备撤回.")
        reason = f"[联防黑名单]-{ blacklist.data[sender_id].get("reason")}"
        need_recall = True

    hallOfShameSettings = mem_cache.get(f"{ group_id }.hall_of_shame_enabled", HallOfShame.level)
    hallOfShameData = mem_cache.get(HallOfShame.key, {})

    if hallOfShameSettings is True and sender_id in hallOfShameData:
        sdk.logger.info(f"发现封神榜黑名单用户 {sender_id},准备撤回.")
        reason = f"{ HallOfShame.name }"
        need_recall = True

    if not need_recall:
        return

    result = await yunhu.Send.To("group", group_id).Recall(msg_id)
    if result.get("status") != "ok":
        sdk.logger.error(f"撤回消息 {msg_id} 失败, msg: {result.get("message")}")
        return
        
    result = await yunhu.Send.To("group", group_id).Ban(sender_id, duration=600)
    if result.get("status") != "ok":
        sdk.logger.error(f"禁言用户 { sender_id} 失败, msg: {result.get("message")}")
        
    content = (
        "黑名单通知\n"
        f"msg_id: { msg_id }\n"
        f"原因: { reason }\n"
        "如有疑问自行申诉,此看板 10 分钟后过期,如已移出联防黑名单但是还仍因联防黑名单拦截则可能是未及时更新导致,请添加机器人为好友使用 /refresh-unblacklist 手动刷新联防黑名单."
    )
    result = await yunhu.Send.To("group", group_id).Expire(600).ForMember(sender_id).Board("local", 
                                                          content = content,
                                                          content_type = "text")
    if result.get("status") != "ok":
        sdk.logger.error(f"设置群聊 { group_id } 的看板失败, msg: {result.get("message")}")

async def hall_of_shame_settings_handler(event: Event):
    if not is_real_admin(event):
        await event.reply("无权限!", reply_to = event["message_id"])
        return
    
    group_id = event.get_group_id()
    if event.get_command_name() in ["h-on", "开启封神榜黑名单"]:
        mem_cache.set(f"{ group_id }.hall_of_shame_enabled", True)
    else:
        mem_cache.set(f"{ group_id }.hall_of_shame_enabled", False)

    await event.reply(f"设置成功,当前状态 { mem_cache.get(f"{ group_id }.hall_of_shame_enabled") }")

command("h-on", help="开启封神榜黑名单",aliases=["开启封神榜黑名单"])(hall_of_shame_settings_handler)
command("h-off", help="关闭封神榜黑名单",aliases=["关闭封神榜黑名单"])(hall_of_shame_settings_handler)

@command("h-view", help = "查看封神榜黑名单", aliases=["查看封神榜黑名单"])
async def hall_of_shame_view_handler(event: Event):
    group_id = event.get_group_id()
    user_id = event.get_user_id()
    if group_id not in HallOfShame.can_view_group:
        return

    board_content = "黑名单列表:\n"
    if mem_cache.get(HallOfShame.key, {}):
        for black_user_id, black_info in mem_cache.get(HallOfShame.key, {}).items():
            board_content += f"""
- {black_user_id}
  原因: { black_info["reason"] }
  操作时间: { black_info["time"] }
  操作人员: { black_info["operator"] }
"""
    await yunhu.Send.To("group", group_id).ForMember(user_id).Expire(600).Board(board_content, content_type = "markdown")
    await event.reply("请看看板", reply_to = event["message_id"])

async def hall_of_shame_list_handler(event: Event):
    group_id = event.get_group_id()
    if group_id not in HallOfShame.can_view_group:
        return
    
    if not is_admin(event):
        await event.reply("无权限!", reply_to = event["message_id"])
        return

    user_id = event.get_user_id()

    parts = event.get_command_raw().split(maxsplit = 2)

    if len(parts) < 3:
        await event.reply("参数错误./<命令> <用户 ID> <原因>",reply_to = event["message_id"])
        return

    ban_user_id = str(parts[1])
    reason = str(parts[2])

    cmd = event.get_command_name()

    if cmd in ["h-add", "添加封神榜黑名单"]:
        payload = {
            "reason": reason,
            "time": datetime.fromtimestamp(event.get_time()).strftime("%Y-%m-%d %H:%M:%S"),
            "operator": user_id
        }
        mem_cache.set(f"{ HallOfShame.key }.{ ban_user_id }", payload)
        mem_cache.clean(HallOfShame.key)
        await event.reply("添加成功!", reply_to = event["message_id"])
        return
    else:
        mem_cache.delete(f"{ HallOfShame.key }.{ ban_user_id }")
        mem_cache.clean(HallOfShame.key)
        await event.reply("删除成功!", reply_to = event["message_id"])
        return


command("h-add", help = "添加封神榜黑名单", aliases=["添加封神榜黑名单"])(hall_of_shame_list_handler)
command("h-del", help = "删除封神榜黑名单", aliases=["删除封神榜黑名单"])(hall_of_shame_list_handler)

@command("refresh-unblacklist", help= "刷新联防黑名单列表")
async def refresh_unblacklist(event: Event):
        await event.reply("正在刷新联防黑名单...", reply = event["message_id"])
        sdk.logger.info("正在请求黑名单信息...")
        # 获取用户信息
        resp = await (await sdk.client.get("http://yunhu-3254340-yh-unified-blacklist-y1h2.out.jwznb.com/v1/blacklist/list",max_retries=3)).json()
        if not resp:
            sdk.logger.error("获取黑名单失败!")
            content = "获取黑名单失败"
        elif resp.get("msg") != "success":
            sdk.logger.error(f"请求异常, msg: { resp.get("msg") }")
            content = f"请求异常, msg: { resp.get("msg") }"

        blacklist_list = resp['data'].get("blacklist")
        if not blacklist_list:
            sdk.logger.error("未获取到黑名单列表,可能是没有黑名单或后端服务异常.")
            content = "未获取到黑名单列表,可能是没有黑名单或后端服务异常."

        blacklist.data = { user["userId"]: user for user in blacklist_list}
        sdk.logger.info(f"刷新黑名单成功!总共 { len(blacklist.data)} 个用户!")
        content = f"刷新黑名单成功!总共 { len(blacklist.data)} 个用户!"
        await event.reply(content, reply_to = event["message_id"])

async def sync_blacklist() -> dict:
    """同步黑名单信息"""
    while True:
        sdk.logger.debug("正在请求黑名单信息...")
        # 获取用户信息
        resp = await (await sdk.client.get("http://yunhu-3254340-yh-unified-blacklist-y1h2.out.jwznb.com/v1/blacklist/list",max_retries=3)).json()
        if not resp:
            sdk.logger.error("获取黑名单失败!10s 后重试")
            await asyncio.sleep(10)
            continue

        if resp.get("msg") != "success":
            sdk.logger.error(f"请求异常, msg: { resp.get("msg") }")
            await asyncio.sleep(10)
            continue

        blacklist_list = resp['data'].get("blacklist")
        if not blacklist_list:
            sdk.logger.error("未获取到黑名单列表,可能是没有黑名单或后端服务异常.")
            await asyncio.sleep(10)
            continue

        blacklist.data = { user["userId"]: user for user in blacklist_list}
        sdk.logger.info(f"更新黑名单成功,总共 { len(blacklist.data)} 个用户!")

        await asyncio.sleep(60)



# ============================================================
#                      进群退群欢迎相关
# ============================================================

@command("w-in", help= "设置进群欢迎")
async def setjointext_handler(event: Event):
    if not is_real_admin(event):
        await event.reply("无权限!", reply_to = event["message_id"])
        return
    
    group_id = event.get_group_id()
    conv = event.conversation(timeout=60)

    # 询问用户消息类型
    content_type = await conv.choose("请选择消息类型:", ["文本", "Markdown", "HTML", "A2UI"])

    if content_type is None:
        await conv.say("超时,已取消!", reply_to = event["message_id"])
        conv.stop()
        return

    content_type_mapping = {
        0: "text",
        1: "markdown",
        2: "html",
        3: "a2ui"
    }
    content_type = content_type_mapping.get(content_type)

    # 询问消息内容
    await conv.say('请发送消息内容(发送"清空"/"clean"以关闭此功能,keep 不更改)\n可用变量: $avatar $uid $name')
    content = await conv.wait()

    if content:
        content = content.get_text()
    else:
        await conv.say("请求超时!", reply_to = event["message_id"])
        conv.stop()
        return
    
    if content in ["清空", "clean"]:
        mem_cache.delete(f"{group_id}:join_in")
        await event.reply("取消进群欢迎成功!", reply_to = event["message_id"])
        return

    if mem_cache.get(f"{group_id}:join_in.content") and content == "keep":
        mem_cache.set(f"{group_id}:join_in.type", content_type)
        await event.reply("更改消息类型成功!", reply_to = event["message_id"])
        return
    elif content == "keep":
        await event.reply("无进群消息!", reply_to = event["message_id"])
        return

    data = {
        "content": content,
        "type": content_type
    }

    mem_cache.set(f"{group_id}:join_in", data)
    await event.reply("设置进群欢迎成功!")

@command("q-out", help= "设置退群消息")
async def setquittext_handler(event: Event):
    if not is_real_admin(event):
        await event.reply("无权限!", reply_to = event["message_id"])
        return
    
    group_id = event.get_group_id()
    conv = event.conversation(timeout=60)

    # 询问用户消息类型
    content_type = await conv.choose("请选择消息类型:", ["文本", "Markdown", "HTML", "A2UI"])

    if content_type is None:
        await conv.say("超时,已取消!", reply_to = event["message_id"])
        conv.stop()
        return

    content_type_mapping = {
        0: "text",
        1: "markdown",
        2: "html",
        3: "a2ui"
    }
    content_type = content_type_mapping.get(content_type)

    # 询问消息内容
    await conv.say('请发送消息内容(发送"清空"/"clean"以关闭此功能,keep 不更改)\n可用变量: $avatar $uid $name')
    content = await conv.wait()

    if content:
        content = content.get_text()
    else:
        await conv.say("请求超时!", reply_to = event["message_id"])
        conv.stop()
        return
    
    if content in ["清空", "clean"]:
        mem_cache.delete(f"{group_id}:quit_out")
        await event.reply("取消退群欢迎成功!", reply_to = event["message_id"])
        return

    if mem_cache.get(f"{group_id}:quit_out.content") and content == "keep":
        mem_cache.set(f"{group_id}:quit_out.type", content_type)
        await event.reply("更改消息类型成功!", reply_to = event["message_id"])
        return
    elif content == "keep":
        await event.reply("无退群消息!", reply_to = event["message_id"])
        return

    data = {
        "content": content,
        "type": content_type
    }

    mem_cache.set(f"{group_id}:quit_out", data)
    await event.reply("设置退群消息成功!")

async def join_and_quit_msg_handler(event: Event):
    avatar = event.get("yunhu_raw", {}).get("event").get("avatarUrl")
    name = event.get("yunhu_raw", {}).get("event").get("nickname")
    user_id = event.get_user_id()
    group_id = event.get_group_id()
    if event.get_detail_type() == "group_member_increase":
        data = mem_cache.get(f"{group_id}:join_in", {})
    else:
        data = mem_cache.get(f"{group_id}:quit_out", {})
    sdk.logger.info(data)
    content = data.get("content")
    if content is None:
        return
    content = (content
               .replace("$avatar", avatar)
               .replace("$name", name)
               .replace("$uid", user_id))
    content_type = data["type"]
    if content_type == "text":
        await yunhu.Send.To("group", group_id).Text(f"{ content }").At(user_id)
    elif content_type == "markdown":
        await yunhu.Send.To("group", group_id).Markdown(f"{ content }").At(user_id)
    elif content_type == "html":
        await yunhu.Send.To("group", group_id).Html(f"{ content }").At(user_id)
    elif content_type == "a2ui":
        await yunhu.Send.To("group", group_id).A2UI(f"{ content }").At(user_id)
    else:
        sdk.logger.error(f"未知类型 { content_type }")

notice.on_group_increase()(join_and_quit_msg_handler)
notice.on_group_decrease()(join_and_quit_msg_handler)

@command("view-jqmsg", help = "查看进退群消息指令", aliases=["查看进群退群消息"])
async def view_join_and_quit_msg_handler(event: Event):
    group_id = event.get_group_id()
    join_msg_all = mem_cache.get(f"{group_id}:join_in", {})
    join_msg_content = join_msg_all.get("content", "无").replace("`", "")
    join_msg_type = join_msg_all.get("type", "text")

    quit_msg_all = mem_cache.get(f"{group_id}:quit_out", {})
    quit_msg_content = quit_msg_all.get("content", "无").replace("`", "")
    quit_msg_type = quit_msg_all.get("type", "text")

    content = (
        f"群 { group_id } 的进群消息和退群消息:\n"
        f"进群消息:\n"
        f"```{ join_msg_type }\n"
        f"{ join_msg_content }\n"
        f"```\n"
        f"退群消息:\n"
        f"```{ quit_msg_type }\n"
        f"{ quit_msg_content}\n"
        f"```"
    )
    await event.reply(content, method = "markdown", reply_to = event["message_id"])

# @command("cache-debug")
# async def print_mem_cache(event):
#     await event.reply(f"{ mem_cache.cache}")

async def main():
    asyncio.create_task(sync_blacklist())
    await sdk.run(keep_running=True)

if __name__ == "__main__":
    asyncio.run(main())
