"""
ErisPulse 类型存根（自动生成，请勿手动编辑）

由 `epsdk types` 命令根据已安装的模块/适配器生成。
仅导出类型供用户代码作为变量标注使用，**不提供任何运行时实例**。
所有导入都在 ``TYPE_CHECKING`` 下，运行时零开销、零行为改变。

使用方式：
    from _ep_types import MyModule, Yunhu
    from ErisPulse import sdk

    # 用导入的类型标注变量，即可获得 IDE 补全
    my_mod: MyModule = sdk.module.get("MyModule")
    my_mod.hello()                       # ← IDE 能补全 hello

    my_adapter: Yunhu = sdk.adapter.get("yunhu")
    await my_adapter.Send.To("group", "123").Board(...)  # ← 补全平台特有方法

说明：
    - 类型名采用 entry-point 名的 PascalCase 形式（如 ``yunhu`` → ``Yunhu``），
      与传入 ``sdk.adapter.get()`` / ``sdk.module.get()`` 的名称对应
    - 存根仅用于静态类型检查，不含运行时实现
    - 安装/卸载模块/适配器后请重新生成：``epsdk types``
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # 以下类型导入仅在 IDE / 类型检查器中生效，不会被运行时执行。
    # 在用户代码中通过 ``from _ep_types import XxxModule`` 获取类型，
    # 配合 ``my_mod: XxxModule = sdk.module.get('XxxModule')`` 获得补全。

    # ===== 适配器（名称与 sdk.adapter.get() 参数一致）=====
    from YunhuAdapter.Core import YunhuAdapter as Yunhu

    __all__ = ['Yunhu']
