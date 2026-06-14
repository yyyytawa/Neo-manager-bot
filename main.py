"""
my_erispulse_project 主程序

这是 ErisPulse 自动生成的主程序文件
"""

import asyncio
from datetime import datetime
import json
from ErisPulse import sdk
from ErisPulse.Core.Event import command
from ErisPulse.Core import adapter

class settings:
    max_warns = 20 # 最大警告次数

async def get_msg(event, msg_id: str):
    """使用 msg_id 获取消息"""
    token = sdk.config.getConfig("Yunhu_Adapter.bots")['default']["token"]
    rsp = await sdk.client.get(f"https://chat-go.jwzhd.com/open-apis/v1/bot/messages?token={ token }&chat-id={ event.get_group_id() }&chat-type=group&message-id={ msg_id }&before=1")
    msg_tmp = (await rsp.json()).get("data", {}).get("list")
    if not msg_tmp:
        return
    msg = msg_tmp[0]
    if msg.get("msgId") != msg_id:
        return
    return msg

async def get_parent_msg_sender(event, msg_id: str):
    msg = await get_msg(event, msg_id)
    if not msg:
        return
    return msg["senderId"]


def is_real_admin(event) -> bool:
    """判断发送者是否为真的管理员/群主"""
    role = event.get_raw()["event"]["sender"]['senderUserLevel']
    return role in ["owner", "administrator"]

def is_admin(event) -> bool:
    """判断发送者是否为管理员/群主"""
    role = event.get_raw()["event"]["sender"]['senderUserLevel']
    if role in ["owner", "administrator"]:
        return True
    admin = sdk.storage.get(event.get_group_id(),{}).get("admin", [])
    if event.get_user_id() in admin:
        return True
    
    return False

@command("ping", help="Ping")
async def ping_handler(event):
    """测试机器人是否启动"""
    await event.reply("Pong!", reply_to= event['message_id'])

@command("board", help="设置群看板(文本).", aliases=["设置看板"])
async def board_handler(event):
    await setboard_handler(event,"text")

@command("mboard", help="设置群看板(Markdown).", aliases=["设置Markdown看板"])
async def mboard_handler(event):
    await setboard_handler(event,"markdown")

@command("hboard", help="设置群看板(HTML).", aliases=["设置HTML看板"])
async def hboard_handler(event):
    await setboard_handler(event,"html")

async def setboard_handler(event,type: str):
    """设置群看板"""
    if not event.is_group_message():
        await event.reply("此命令仅限群聊使用", reply_to=event["message_id"])
        return

    if not is_admin(event):
        await event.reply("无权限!", reply_to = event["message_id"])
        return

    yunhu = adapter.get("yunhu")
    parts = event.get_command_raw().split(maxsplit=1)
    content = parts[1] if len(parts) > 1 else ""

    if content == "":
        result = await yunhu.Send.To("group", event.get_group_id()).DismissBoard("local")
    else:
        result = await yunhu.Send.To("group", event.get_group_id()).Board("local", content = content, content_type = type)
    
    if result.get("status") == "ok":
        await event.reply("设置成功!", reply_to = event["message_id"])
    else:
        await event.reply(f"设置失败! msg: { result.get("message") }")

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

    yunhu = adapter.get("yunhu")
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

    yunhu = adapter.get("yunhu")
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
    yunhu = adapter.get("yunhu")
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
    data = sdk.storage.get(f"{group_id}", {})
    admin_list = data.get("admin", [])
    admin_list = list(set(admin_list + args))
    if len(admin_list) > 100:
        await event.reply("长度超限!请先删除一部分管理员.", reply_to = event["message_id"])
        return
    data["admin"] = admin_list
    sdk.storage.set(f"{group_id}", data)
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
    data = sdk.storage.get(f"{group_id}", {})
    admin_list = set(data.get("admin", []))
    admin_list.difference_update(args)
    data["admin"] = list(admin_list)
    sdk.storage.set(f"{group_id}", data)
    await event.reply("删除成功!", reply_to = event["message_id"])

@command("adminlist", help = "查看管理员列表", aliases=["查看管理员列表"])
async def adminlist_handler(event):
    group_id = event.get_group_id()
    admin_list = sdk.storage.get(f"{group_id}", {}).get("admin", [])
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

    yunhu = adapter.get("yunhu")
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
    data = sdk.storage.get(f"warns:{group_id}:{parent_msg_sender}", [])
    data.insert(0, payload)
    if len(data) > settings.max_warns:
        data = data[:settings.max_warns]
    sdk.storage.set(f"warns:{group_id}:{parent_msg_sender}", data)
    await event.reply(f"成功警告用户 {parent_msg_sender}.\n原因: {reason}.\n当前用户的警告次数为 {len(data)}.")

@command("warndel", help = "撤销最近一次的警告")
async def warndel_handler(event):
    """撤销最近的一次警告"""
    if not is_admin(event):
        await event.reply("无权限!", reply_to = event["messa ge_id"])
        return
    parts = event.get_command_raw().split(maxsplit=1)
    user_id = parts[1] if len(parts) > 1 else ""
    if not user_id:
        await event.reply("参数错误!用法: /warndel <用户 ID>", reply_to = event["message_id"])
        return
    elif len(user_id) > 20:
        await event.reply("用户 ID 过长!", reply_to = event["message_id"])
        return

    warns = sdk.storage.get(f"warns:{event.get_group_id()}:{user_id}", [])
    warns = warns[1:]
    sdk.storage.set(f"warns:{event.get_group_id()}:{user_id}", warns)
    await event.reply(f"成功撤销用户 {user_id} 最近的一次警告!")

@command("warns", help = "查看警告记录")
async def warns_handler(event):
    parts = event.get_command_raw().split(maxsplit=1)
    user_id = parts[1] if len(parts) > 1 else ""
    if not user_id:
        user_id = event.get_user_id()

    group_id = event.get_group_id()
    warns = sdk.storage.get(f"warns:{group_id}:{user_id}", [])
    content = f"<details>{user_id} 在群 {group_id} 被警告信息\n"
    for warn in warns:
        warn_time = datetime.fromtimestamp(warn["time"]).strftime("%Y-%m-%d %H:%M:%S")
        warn_msg_raw = json.dumps(warn["msg_raw"], indent= 2)
        content += f"警告时间: {warn_time}\n原因: {to_html_entities(warn["reason"])}\n操作者: {warn["operator"]}\n被警告的信息元数据:\n{to_html_entities(warn_msg_raw)}\n"
    content += f"总计: {len(warns)} 条.</details>"
    await event.reply(content, method = "Markdown", reply_to = event["message_id"])

async def main():
    await sdk.run(keep_running=True)

if __name__ == "__main__":
    asyncio.run(main())
