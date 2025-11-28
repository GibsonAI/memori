#!/usr/bin/env python3
"""
测试 FTS contentless 和 category_primary 修复

运行方法：
cd memori && python -m pytest tests/test_fts_fix.py -v
或直接运行：
cd memori && python tests/test_fts_fix.py
"""

import os
import sys
import tempfile
import time

# 添加 memori 模块路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from memori import Memori


def test_basic_memory_retrieval():
    """测试基础记忆写入和检索"""
    print("\n" + "=" * 60)
    print("测试 1: 基础记忆写入和检索")
    print("=" * 60)

    # 使用临时数据库
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        # 创建 Memori 实例
        memori = Memori(
            database_connect=f"sqlite:///{db_path}",
            user_id="test_user_fts_fix",
            conscious_ingest=True,
            auto_ingest=False,
            schema_init=True,
        )
        memori.enable()

        # 写入一些对话
        print("\n📝 写入对话记忆...")
        memori.record_conversation(
            user_input="我叫张三，我是一名软件工程师，我喜欢打篮球。",
            ai_output="你好张三！很高兴认识你。软件工程师是个很棒的职业。",
            model="gpt-4",
        )

        # 等待异步处理完成
        print("⏳ 等待记忆处理...")
        time.sleep(3)

        # 检索记忆
        print("\n🔍 检索记忆（查询：张三）...")
        memories = memori.retrieve_context(query="张三是谁", limit=5)

        print(f"\n📊 检索结果：找到 {len(memories)} 条记忆")
        for i, m in enumerate(memories):
            content = m.get("searchable_content", m.get("summary", "N/A"))
            print(f"  [{i+1}] {content[:80]}...")

        # 验证
        if len(memories) > 0:
            content_str = str(memories)
            if "张三" in content_str:
                print("\n✅ 测试通过：成功检索到张三的信息")
                return True
            else:
                print("\n❌ 测试失败：检索到记忆但不包含张三的信息")
                return False
        else:
            print("\n❌ 测试失败：没有检索到任何记忆")
            return False

    finally:
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_get_essential_conversations():
    """测试 get_essential_conversations 方法"""
    print("\n" + "=" * 60)
    print("测试 2: get_essential_conversations 方法")
    print("=" * 60)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        memori = Memori(
            database_connect=f"sqlite:///{db_path}",
            user_id="test_user_essential",
            conscious_ingest=True,
            auto_ingest=False,
            schema_init=True,
        )
        memori.enable()

        # 写入对话
        print("\n📝 写入对话记忆...")
        memori.record_conversation(
            user_input="请记住：我的密码提示是 blue-sky-2024",
            ai_output="好的，我记住了你的密码提示。",
            model="gpt-4",
        )

        # 等待处理
        print("⏳ 等待记忆处理...")
        time.sleep(3)

        # 调用 get_essential_conversations
        print("\n🔍 调用 get_essential_conversations...")
        essential = memori.get_essential_conversations(limit=10)

        print(f"\n📊 Essential 结果：找到 {len(essential)} 条")
        for i, e in enumerate(essential):
            content = e.get("searchable_content", e.get("summary", "N/A"))
            category = e.get("category_primary", "N/A")
            print(f"  [{i+1}] category={category}, content={content[:60]}...")

        if len(essential) > 0:
            print("\n✅ 测试通过：get_essential_conversations 返回了结果")
            return True
        else:
            print("\n❌ 测试失败：get_essential_conversations 返回空")
            return False

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_fts_search():
    """测试 FTS 搜索功能"""
    print("\n" + "=" * 60)
    print("测试 3: FTS 全文搜索功能")
    print("=" * 60)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        memori = Memori(
            database_connect=f"sqlite:///{db_path}",
            user_id="test_user_fts",
            conscious_ingest=True,
            auto_ingest=False,
            schema_init=True,
        )
        memori.enable()

        # 写入多条对话
        print("\n📝 写入多条对话...")
        conversations = [
            ("我喜欢喝咖啡，特别是拿铁。", "咖啡是很好的提神饮品。"),
            ("我的生日是3月15日。", "我会记住你的生日。"),
            ("我在北京工作，是一名程序员。", "北京是个很棒的城市。"),
        ]

        for user_input, ai_output in conversations:
            memori.record_conversation(
                user_input=user_input, ai_output=ai_output, model="gpt-4"
            )
            print(f"  ✓ {user_input[:30]}...")

        # 等待处理
        print("⏳ 等待记忆处理...")
        time.sleep(5)

        # 测试不同的搜索词
        test_queries = ["咖啡", "生日", "北京"]

        all_passed = True
        for query in test_queries:
            print(f"\n🔍 搜索：{query}")
            memories = memori.retrieve_context(query=query, limit=5)
            print(f"   找到 {len(memories)} 条记忆")

            if len(memories) == 0:
                print(f"   ❌ 搜索 '{query}' 没有结果")
                all_passed = False
            else:
                print(f"   ✅ 搜索 '{query}' 成功")

        if all_passed:
            print("\n✅ 所有搜索测试通过")
            return True
        else:
            print("\n❌ 部分搜索测试失败")
            return False

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def main():
    print("\n" + "🔧 FTS 修复验证测试" + "\n")

    results = []

    # 运行测试
    tests = [
        ("基础记忆检索", test_basic_memory_retrieval),
        ("Essential Conversations", test_get_essential_conversations),
        ("FTS 全文搜索", test_fts_search),
    ]

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 出错：{e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 所有测试通过！修复有效。")
    else:
        print("\n⚠️ 部分测试失败，需要继续调查。")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

