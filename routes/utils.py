# routes/utils.py
import sqlite3

def get_or_create_tags(db, tag_names):
    """
    辅助函数：获取或创建标签，并返回它们的ID。
    db: 数据库连接对象
    tag_names: 标签名称列表
    """
    tag_ids = []
    for tag_name in tag_names:
        tag_name = tag_name.strip()
        if not tag_name: # 忽略空字符串标签
            continue

        # 检查标签是否已存在
        cursor_select = db.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
        tag = cursor_select.fetchone() # 从查询游标获取结果

        if tag:
            tag_ids.append(tag['id'])
        else:
            # 如果标签不存在，则插入新标签
            cursor_insert = db.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
            # 从执行 INSERT 操作的游标对象获取 lastrowid
            tag_ids.append(cursor_insert.lastrowid)
    return tag_ids